"""手順5: 組の期待値で組を選ぶ買い方（ワイド・馬連・馬単・3連複・3連単）を作って確かめる（研究「複勝以外の回収率100超」の入口④。docs/04）。

    uv run python research/複勝以外の回収率100超/combo_value.py mark --from-year 2019   # 2019年からの当日の予測に印を付ける（15分ほど）
    uv run python research/複勝以外の回収率100超/combo_value.py fit                     # 2023〜2026年で、券種ごとの組の確率の重みを推定する
    uv run python research/複勝以外の回収率100超/combo_value.py grid                    # 2023〜2026年で、線 × 上限 × 対象を数える（選ぶ）
    uv run python research/複勝以外の回収率100超/combo_value.py check                   # 道具「印の成績」の買い目から、期間ごとの成績と運用の目安を出す

``mark`` は ``early_years.py combine`` が作った予測（``predictions-2019から/`` か ``predictions-2021から/``）に、道具「印の成績」と同じ決め方で印を付け、
``組の期待値/marked-<年>から.parquet`` に書く。``fit`` と ``grid`` は、その表と元DB の確定オッズの板・払戻の明細から、本番と同じ部品（``yosou.shared.combo_value``）で
組の表を月ごとに作る（3連単は組が多いので、レースID を 3 で割った余りが 0 のレースだけ）。``fit`` は重みを ``組の期待値/combo_blend.json`` に書く
（``--save-models`` で本番のモデルの置き場所にも書く）。``check`` は、道具「印の成績」を 2019年からの予測で回した買い目の CSV
（``印の成績-2019から/買い目/``）から数える。出るものは全部 Git 対象外の ``reports/複勝以外の回収率100超/組の期待値/``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from 共通 import db  # noqa: E402

from yosou.shared.betting import TicketType  # noqa: E402
from yosou.shared.combo_value import ComboBlend, ComboBlendFitter  # noqa: E402
from yosou.shared.repository import ComboBlendWeightsRepository  # noqa: E402

from 今週の予想.model_folders import DEFAULT_MODELS  # noqa: E402
from 今週の予想.ticket_rules import COMBO_VALUE_RULES  # noqa: E402
from 複勝以外の回収率100超.analysis.backtest_marking import BacktestMarking  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_month_frames import ComboMonthFrames  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_operation_report import ComboOperationReport  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_period_report import ComboPeriodReport  # noqa: E402
from 複勝以外の回収率100超.analysis.combo_rule_grid import ComboRuleGrid  # noqa: E402

_REPORTS = Path(__file__).resolve().parents[2] / "reports"
ROOT = _REPORTS / "複勝以外の回収率100超"
OUT = ROOT / "組の期待値"
#: 重みと線を決める開発の期間（今の本番の7つの区切りのテスト期間）。
DEV_YEARS = (2023, 2026)
#: 券種（docs/04 の順）。3連単は組の表を軽くするため、3つに1つのレースだけ使う。
TICKET_TYPES = (TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA, TicketType.TRIO, TicketType.TRIFECTA)
SAMPLE = {TicketType.TRIFECTA: 3}
#: 実際に買う買い方と、1点の重み（組の期待値用の財布の割合 馬連 0.02%・馬単 0.04% の比）。
OPERATION_WEIGHTS = {"馬連（組の期待値）": 1.0, "馬単（組の期待値）": 2.0}


def main() -> None:
    args = _parser().parse_args()
    {"mark": _mark, "fit": _fit, "grid": _grid, "check": _check}[args.step](args)


def _mark(args: argparse.Namespace) -> None:
    with db.open_db(args.db) as con:
        marked = BacktestMarking(ROOT / f"predictions-{args.from_year}から", DEFAULT_MODELS).mark(con)
    path = OUT / f"marked-{args.from_year}から.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    marked.to_parquet(path)
    print(f"{len(marked):,}頭・{marked['race_id'].nunique():,}レース → {path}", flush=True)


def _dev_frames(args: argparse.Namespace) -> dict[TicketType, pd.DataFrame]:
    """開発の期間の、券種ごとの組の表（月ごとに作ってつなぐ）。"""
    marked = pd.read_parquet(OUT / f"marked-{args.from_year}から.parquet")
    years = pd.to_datetime(marked["race_date"]).dt.year
    marked = marked[years.between(*DEV_YEARS)]
    parts: dict[TicketType, list[pd.DataFrame]] = {ticket_type: [] for ticket_type in TICKET_TYPES}
    with db.open_db(args.db) as con:
        frames = ComboMonthFrames(con, SAMPLE)
        for month, group in marked.groupby(pd.to_datetime(marked["race_date"]).dt.to_period("M"), sort=True):
            print(f"組の表: {month}", file=sys.stderr, flush=True)
            for ticket_type, frame in frames.build(group, TICKET_TYPES).items():
                parts[ticket_type].append(frame)
    return {ticket_type: pd.concat(frames_of, ignore_index=True) for ticket_type, frames_of in parts.items()}


def _fit(args: argparse.Namespace) -> None:
    frames = _dev_frames(args)
    weights = {ticket_type: ComboBlendFitter().fit(frame) for ticket_type, frame in frames.items()}
    for ticket_type, value in weights.items():
        print(f"{ticket_type.label}: {value}", flush=True)
    print(ComboBlendWeightsRepository(OUT).save(weights), flush=True)
    if args.save_models:
        print(ComboBlendWeightsRepository(DEFAULT_MODELS).save(weights), flush=True)


def _grid(args: argparse.Namespace) -> None:
    weights = ComboBlendWeightsRepository(OUT).load()
    lines = []
    for ticket_type, frame in _dev_frames(args).items():
        valued = ComboBlend().of(ticket_type, frame, weights[ticket_type])
        table = ComboRuleGrid().table(ticket_type, valued)
        lines += [f"\n## {ticket_type.label}\n", table.head(args.top).to_markdown(index=False)]
    _write(OUT / "線と上限の選び方.md", "# 線・オッズの上限・対象の選び方（2023〜2026年だけ。幅の下の端の高い順）\n" + "\n".join(lines))


def _check(args: argparse.Namespace) -> None:
    tickets = pd.read_csv(args.tickets, dtype={"レースID": str, "組番": str})
    labels = tuple(rule.label for rule in COMBO_VALUE_RULES)
    periods, yearly = ComboPeriodReport().tables(tickets, labels)
    days = pd.read_parquet(OUT / f"marked-{args.from_year}から.parquet", columns=["race_date"])["race_date"].nunique()
    report = ComboOperationReport()
    text = ["# 組の期待値の買い方の成績（当日の予想・確定オッズ・1点 100円）\n", periods.to_markdown(index=False),
            "\n\n## 年ごとの回収率（%）\n", yearly.to_markdown(),
            f"\n\n## 運用の目安（馬連 1点・馬単 2点の重み。1点 = 100円）\n", *report.lines(tickets, OPERATION_WEIGHTS, days), "",
            report.yearly(tickets, OPERATION_WEIGHTS).to_markdown()]
    _write(OUT / "確かめの結果.md", "\n".join(text))


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")
    print(text, flush=True)
    print(f"\n保存先: {path}", file=sys.stderr)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="組の期待値で組を選ぶ買い方を作って確かめる（docs/04）", allow_abbrev=False)
    parser.add_argument("step", choices=("mark", "fit", "grid", "check"), help="mark・fit・grid・check")
    parser.add_argument("--from-year", choices=("2019", "2021"), default="2019", help="使う予測（predictions-<年>から。既定: 2019）")
    parser.add_argument("--save-models", action="store_true", help="fit で、本番のモデルの置き場所にも重みを書く")
    parser.add_argument("--top", type=int, default=8, help="grid で、券種ごとに出す行の数（既定: 8）")
    parser.add_argument("--tickets", type=Path, default=ROOT / "印の成績-2019から" / "買い目" / "dscore_race_day_top3-race_day.csv",
                        help="check で読む、道具「印の成績」の買い目の CSV")
    parser.add_argument("--db", type=Path, default=None, help="元DB の場所")
    return parser


if __name__ == "__main__":
    main()
