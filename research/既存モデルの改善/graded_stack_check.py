"""重賞の二段の予想（2案目）を、テストの年ごとに確かめる（研究「既存モデルの改善」の入口⑯）。

    uv run python research/既存モデルの改善/graded_stack_check.py build     # 重賞の行の表を作る（W を元DB から読む。1分ほど）
    uv run python research/既存モデルの改善/graded_stack_check.py run       # 2016〜2026年を1年ずつ、その年より前の重賞で2段目を学んで予測する（数分）
    uv run python research/既存モデルの改善/graded_stack_check.py summary   # 重賞の行のログ損失を、1段目・当日の手本と比べる

1段目は、今の本番の前日と同じ作りを1年ずつの区切りで学んだ予測（入口⑮ の ``dayb-*``。テスト 2015〜2026年。どの年も、その年より前だけで学んだもの）。
2段目は、重賞の行だけで「1段目と市場の見立ての、重賞でのずれ」を直す（3着以内はずらしのロジスティック回帰、1着はレースの中の条件付きロジット）。
確定オッズから見た確率と W（重賞の格と実績）・K（その重賞の傾向）を材料にする。出るもの（Git 対象外）: ``tables/graded_stack.pkl``・
``predictions/graded_race_day/stack-top3.pkl``・``stack-win.pkl``・``compare/重賞の二段の予想-<日付>.md``。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.shared.dataset import HORSE_ID, RACE_ID  # noqa: E402
from yosou.stakes_tendency_top3.feature import RACE_DAY_CATALOG as STAKES_RACE_DAY_CATALOG  # noqa: E402

from 既存モデルの改善.analysis.development_score.score_tables import score_table_named  # noqa: E402
from 既存モデルの改善.analysis.graded_race import K_NAMES, PREDICTION_TABLE, GradedMaterialReader  # noqa: E402
from 既存モデルの改善.analysis.graded_stack import StackTableBuilder, YearlyStackRunner  # noqa: E402
from 既存モデルの改善.analysis.graded_stack.stack_table_builder import YEAR, Y_TOP3, Y_WIN  # noqa: E402
from 既存モデルの改善.analysis.tables import TableStore  # noqa: E402
from 既存モデルの改善.analysis.walk_forward import PredictionStore  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports" / "既存モデルの改善"
_TABLES, _PREDICTIONS = _REPORTS / "tables", _REPORTS / "predictions"
_STACK_TABLE = _TABLES / "graded_stack.pkl"
#: 1段目の元の表と予測（テスト 2015〜2019年と 2020〜2026年）。
_BASE_TABLE = "dscore_day_before"
_BASE = {"top3": ("dayb-top3-early", "dayb-top3"), "win": ("dayb-win-early", "dayb-win")}
#: 比べる相手（当日の手本。入口⑮ の general-*。テスト 2020〜2026年）。
_GENERAL = {"top3": "general-top3", "win": "general-win"}
#: 2段目で予測するテストの年（2015年は学ぶ年が無い）。
YEARS = tuple(range(2016, 2027))
_EPS = 1e-15


def main() -> None:
    args = _parser().parse_args()
    {"build": _build, "run": _run, "summary": _summary}[args.step](args)


def _build(args: argparse.Namespace) -> None:
    with db.open_db(args.db) as con:
        materials = GradedMaterialReader(con).read(date(2012, 1, 1))
    tables, predictions = TableStore(_TABLES), PredictionStore(_PREDICTIONS)
    stakes = tables.read("stakes_race_day", STAKES_RACE_DAY_CATALOG)
    tendency = pd.DataFrame({"race_id": stakes.ids[RACE_ID].astype(str).to_numpy(), "horse_id": stakes.ids[HORSE_ID].astype(str).to_numpy(),
                             **{name: stakes.features[name].to_numpy() for name in K_NAMES}})
    base = {target: pd.concat([predictions.read(PREDICTION_TABLE, key) for key in keys], ignore_index=True) for target, keys in _BASE.items()}
    table = tables.read(_BASE_TABLE, score_table_named(_BASE_TABLE).catalog)
    stack = StackTableBuilder().build(table, base["top3"], base["win"], materials, tendency)
    stack.to_pickle(_STACK_TABLE)
    print(f"重賞の行 {len(stack):,}・重賞 {stack['race_id'].nunique():,}レース（{stack[YEAR].min()}〜{stack[YEAR].max()}年）→ {_STACK_TABLE}")


def _run(args: argparse.Namespace) -> None:
    table = pd.read_pickle(_STACK_TABLE)
    top3, win, log = YearlyStackRunner().run(table, YEARS)
    store = PredictionStore(_PREDICTIONS)
    print(store.write(PREDICTION_TABLE, "stack-top3", top3, log))
    print(store.write(PREDICTION_TABLE, "stack-win", win, log))
    print(log.to_string(index=False))


def _summary(args: argparse.Namespace) -> None:
    table = pd.read_pickle(_STACK_TABLE)
    store = PredictionStore(_PREDICTIONS)
    lines = [f"# 重賞の二段の予想: テストの年の重賞の行のログ損失（{date.today().isoformat()}）", "",
             "小さいほど良い。1段目 = 今の本番の前日の作り、当日の手本 = 今の本番の当日の作り（2020年から）。同じ行だけで比べる。", ""]
    for target, label in (("top3", Y_TOP3), ("win", Y_WIN)):
        frames = {"二段の予想": _probability(store, f"stack-{target}"), "1段目（前日）": _probability(store, *_BASE[target]),
                  "当日の手本": _probability(store, _GENERAL[target])}
        rows = table[["race_id", "horse_id", YEAR, label]]
        for name, frame in frames.items():
            rows = rows.merge(frame.rename(columns={"p": name}), on=["race_id", "horse_id"], how="left")
        lines += [f"## {'3着以内' if target == 'top3' else '1着'}", "", "| 年 | 行数 | " + " | ".join(frames) + " | 二段が1段目より小さい |",
                  "|---|---|" + "---|" * len(frames) + "---|"]
        for year, group in [*rows[rows[YEAR].isin(YEARS)].groupby(YEAR), ("全体", rows[rows[YEAR].isin(YEARS)])]:
            losses = {name: _logloss(group[label], group[name]) for name in frames}
            lines.append(f"| {year} | {len(group):,} | " + " | ".join(f"{losses[name]:.5f}" for name in frames)
                         + f" | {'○' if losses['二段の予想'] < losses['1段目（前日）'] else '×'} |")
        later = rows[rows[YEAR] >= 2020].dropna(subset=["当日の手本"])
        lines += ["", f"2020年からで当日の手本と同じ行: 二段 {_logloss(later[label], later['二段の予想']):.5f}・当日の手本 {_logloss(later[label], later['当日の手本']):.5f}", ""]
    out = _REPORTS / "compare" / f"重賞の二段の予想-{date.today().isoformat()}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def _probability(store: PredictionStore, *keys: str) -> pd.DataFrame:
    frame = pd.concat([store.read(PREDICTION_TABLE, key) for key in keys], ignore_index=True)
    frame = frame[frame["期間"] == "テスト"]
    return pd.DataFrame({"race_id": frame[RACE_ID].astype(str), "horse_id": frame[HORSE_ID].astype(str), "p": frame["確率"]}).drop_duplicates(
        ["race_id", "horse_id"], keep="last")


def _logloss(y: pd.Series, p: pd.Series) -> float:
    mask = p.notna()
    actual, prob = y[mask].to_numpy(dtype=float), np.clip(p[mask].to_numpy(dtype=float), _EPS, 1 - _EPS)
    return float(-np.mean(actual * np.log(prob) + (1 - actual) * np.log(1 - prob)))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="重賞の二段の予想の確かめ", allow_abbrev=False)
    parser.add_argument("step", choices=("build", "run", "summary"))
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
