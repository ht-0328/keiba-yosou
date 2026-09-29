"""保存した予測から、◎と1番人気を比べた表を書く（研究「一番人気を疑う」の入口③）。

    uv run --with pyarrow --with tabulate python research/一番人気を疑う/summarize.py

``run_experiments.py`` が保存した予測を全部読み、``reports/一番人気を疑う/結果.md``（Git 対象外）に書く。
条件ごとの表と、◎の確率の帯の表は、``--detail`` で選んだ作り方（既定は今の予想の木曜版と、木曜の197個の材料）について出す。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 一番人気を疑う.analysis.evaluation import (  # noqa: E402
    ConfidenceBands,
    DoubtBreakdown,
    TopPickSummary,
    TopPickTable,
)
from 一番人気を疑う.analysis.experiments import EXPERIMENTS  # noqa: E402
from 一番人気を疑う.analysis.source import MarketPredictionSource  # noqa: E402

DEFAULT_PREDICTIONS = Path("reports/一番人気を疑う/予測")
DEFAULT_OUT = Path("reports/一番人気を疑う/結果.md")
DEFAULT_DETAIL = ("00_今の予想_木曜", "21_木曜_研究の材料")
DEFAULT_TABLES = Path("reports/既存モデルの改善/tables")
DEFAULT_MARKET = Path("reports/既存モデルの改善/predictions")
#: 比べる、オッズを使う作り方（予想の名前, 作り方, 表に出す名前）。
MARKET_VARIANTS: tuple[tuple[str, str, str], ...] = (
    ("form_aptitude_top3", "current", "今の予想の当日版（直す前。単勝オッズを使う）"),
    ("form_aptitude_top3", "odds_only", "単勝オッズだけ"),
    ("form_aptitude_top3", "improved", "今の予想の当日版（単勝オッズを基準に補正）"),
    ("form_experiments", "pool", "今の予想の当日版 ＋ 券種ごとのオッズから見た支持"),
)
#: 条件ごとの表の切り口（列の名前 → 表に出す名前）。表によって列の名前が違う。
_CONDITIONS = {"クラス": "クラス", "class_name": "クラス", "芝ダ": "芝ダ", "surface": "芝ダ",
               "1番人気の出走数": "1番人気の出走数", "1番人気のオッズ": "1番人気の単勝オッズ", "◎の人気": "◎の人気",
               "確信の強さ": "◎と1番人気の確率の差（疑ったレースを4つに等分）"}


def main() -> None:
    parser = argparse.ArgumentParser(description="◎と1番人気を比べた表を書く", allow_abbrev=False)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--detail", nargs="*", default=list(DEFAULT_DETAIL))
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES, help="研究「既存モデルの改善」の表")
    parser.add_argument("--market", type=Path, default=DEFAULT_MARKET, help="研究「既存モデルの改善」の予測")
    args = parser.parse_args()
    races = {experiment.key: TopPickTable().build(pd.read_parquet(path))
             for experiment in EXPERIMENTS if (path := args.predictions / f"{experiment.key}.parquet").exists()}
    labels = {experiment.key: experiment.label for experiment in EXPERIMENTS}
    summary = pd.DataFrame([{**TopPickSummary().row(table, key), "説明": labels[key]} for key, table in races.items()])
    lines = ["# 一番人気を疑う — 結果", "", "JV-Data 由来の値を含むため、この文書は Git の対象外。", "",
             "## 1. 作り方ごとの◎と1番人気（7つの区切りのテスト期間の合計）", "", summary.to_markdown(index=False), ""]
    lines += _market(MarketPredictionSource(args.tables, args.market))
    for key in args.detail:
        if key in races:
            lines += _detail(key, races[key])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出しました: {args.out}", flush=True)


def _market(source: MarketPredictionSource) -> list[str]:
    """オッズを使う作り方の◎と1番人気（研究「既存モデルの改善」の予測。同じ7つの区切り）。"""
    rows = [TopPickSummary().row(TopPickTable().build(source.read(model, key)), label) for model, key, label in MARKET_VARIANTS]
    return ["## 2. オッズを使う作り方の◎と1番人気（研究「既存モデルの改善」の予測。確定オッズ）", "",
            pd.DataFrame(rows).to_markdown(index=False), "",
            "締め切り前のオッズでの確かめは `締め切り前での確かめ.md`（`pre_deadline_check.py`）。", ""]


def _detail(key: str, races: pd.DataFrame) -> list[str]:
    races = _with_conditions(races)
    lines = [f"## {key}: 疑ったレースを条件ごとに分けたとき", ""]
    for column, title in _CONDITIONS.items():
        if column in races.columns:
            lines += [f"### {title}", "", DoubtBreakdown().by(races, column).to_markdown(), ""]
    lines += [f"## {key}: ◎の確率の帯ごと", "", ConfidenceBands().table(races).to_markdown(), ""]
    return lines


def _with_conditions(races: pd.DataFrame) -> pd.DataFrame:
    """条件ごとの表の切り口の列を足す（1番人気の出走数・単勝オッズ・◎の人気・確信の強さ）。"""
    races = races.copy()
    runs = next((f"{name}_1番人気" for name in ("runs_before", "通算の出走数") if f"{name}_1番人気" in races), None)
    if runs is not None:
        races["1番人気の出走数"] = pd.cut(races[runs], [-1, 0, 2, 5, 1000], labels=["0（新馬）", "1〜2", "3〜5", "6〜"])
    races["1番人気のオッズ"] = pd.cut(races["確定の単勝オッズ_1番人気"], [0, 1.9, 2.9, 3.9, 1000],
                                 labels=["〜1.9倍", "2.0〜2.9倍", "3.0〜3.9倍", "4.0倍〜"])
    races["◎の人気"] = races["確定の単勝人気"].clip(upper=6).astype(int).astype(str).replace("6", "6〜")
    doubted = races["疑った"]
    races.loc[doubted, "確信の強さ"] = pd.qcut(races.loc[doubted, "score"] - races.loc[doubted, "score_1番人気"], 4,
                                          labels=["弱い", "やや弱い", "やや強い", "強い"]).astype(str)
    return races


if __name__ == "__main__":
    main()
