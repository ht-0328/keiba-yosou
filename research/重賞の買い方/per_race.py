"""研究「重賞の買い方」2回目の入口: レースの型ごとに券種と買い方を1つ選び、重賞の 2021〜2026年で確かめる（docs/03）。

    uv run python research/重賞の買い方/per_race.py count   # 重賞だけで、型（24 セル）ごとに 8券種の候補を数え上げる（2回目/候補/<券種>.npz）
    uv run python research/重賞の買い方/per_race.py pick    # 全レースの 2015〜2020年で、型ごとに券種と買い方を1つ選ぶ（2回目/選んだ券種.md・.json）
    uv run python research/重賞の買い方/per_race.py check   # 重賞の 2021〜2026年で一度だけ数える（2回目/確かめ.md）

先に ``stakes_bets.py races`` と、研究「全レース全券種の買い方」の材料と ``候補/<券種>.npz`` が要る。出るものは Git 対象外の ``reports/重賞の買い方/2回目/``。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from 共通 import render  # noqa: E402
from 共通.render import Table  # noqa: E402

from 全レース全券種の買い方.analysis.candidate_counter import CandidateCounter  # noqa: E402
from 全レース全券種の買い方.analysis.cell_selector import CellChoice, CellSelector  # noqa: E402
from 全レース全券種の買い方.analysis.choice_summary import ChoiceSummary  # noqa: E402
from 全レース全券種の買い方.analysis.combos_source import BRACKET_LABEL, TICKET_LABELS  # noqa: E402
from 全レース全券種の買い方.analysis.day_table import HIT_RACES, PAYOUT, POINTS, RACES  # noqa: E402
from 全レース全券種の買い方.analysis.formation import MAX_POINTS, candidates  # noqa: E402
from 全レース全券種の買い方.analysis.horse_slots import HorseSlots  # noqa: E402
from 全レース全券種の買い方.formations import CELLS, _source  # noqa: E402
from 全レース全券種の買い方.materials import MARKED, OUT as ALL_RACES_OUT  # noqa: E402
from 重賞の買い方.analysis import GradedCells, PlaceBaseline, TicketChooser  # noqa: E402
from 重賞の買い方.stakes_bets import GRADED, OUT as STAKES_OUT  # noqa: E402

OUT = STAKES_OUT / "2回目"
SELECT_YEARS = range(2015, 2021)
CONFIRM_YEARS = range(2021, 2027)
ALL_YEARS = range(2015, 2027)
#: 比べる相手の ◎ の単勝（単勝の型の「◎ − 相手 2頭・流し・絞らない」は ◎ の単勝1点）。
TOP_WIN = "◎ − 相手 2頭・流し・絞らない・12点まで"


def main() -> None:
    args = _parser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"count": _count, "pick": _pick, "check": _check}[args.command](args)


def _cells_table() -> pd.DataFrame:
    return GradedCells().build(pd.read_parquet(ALL_RACES_OUT / "等級.parquet"), pd.read_parquet(GRADED), full=True)


def _count(args: argparse.Namespace) -> None:
    marked = pd.read_parquet(MARKED)
    cells_table = _cells_table()
    print(f"重賞 {len(cells_table):,} レース", file=sys.stderr, flush=True)
    source = _source(marked, HorseSlots().build(marked), cells_table)
    days = sorted(pd.to_datetime(cells_table["race_date"]).drop_duplicates())
    for label in TICKET_LABELS:
        formations = [formation for formation in candidates(label) if formation.max_points == MAX_POINTS]
        counter = CandidateCounter(source, label, formations, CELLS, days)
        counter.count([year for year in ALL_YEARS if not (label == BRACKET_LABEL and year == 2015)])
        print(f"  保存: {counter.save(OUT / '候補' / f'{label}.npz')}", file=sys.stderr, flush=True)


def _pick(args: argparse.Namespace) -> None:
    """全レースの数え上げ（研究「全レース全券種の買い方」の候補）で、2015〜2020年だけを見て、券種ごと → 券種どうしの順に選ぶ。"""
    per_ticket: dict[str, list[CellChoice]] = {}
    for label in TICKET_LABELS:
        values, cells, days, labels = CandidateCounter.load(ALL_RACES_OUT / "候補" / f"{label}.npz")
        if list(cells) != list(CELLS):
            raise ValueError("全レースの数え上げのセルの並びが合っていません")
        day_mask = np.array([day.year in SELECT_YEARS for day in days])
        per_ticket[label] = CellSelector(labels, cells, formations=candidates(label)).select(values, day_mask)
    chosen = TicketChooser().choose(per_ticket, CELLS)
    rows = [[cell, item.ticket, item.choice.label, _pct(item.choice.recovery), _pct(item.choice.lower), item.choice.hits, item.choice.races,
             f"{item.choice.points_per_race:.1f}", "" if item.choice.enough else "当たり不足"] for cell, item in zip(CELLS, chosen, strict=True)]
    table = Table(["型", "券種", "買い方", "回収率", "下の端", "当たったレース", "レース", "1レースの点数", "注意"], rows,
                  title=f"型ごとに選んだ券種と買い方（全レースの {SELECT_YEARS.start}〜{SELECT_YEARS.stop - 1}年）",
                  note="券種ごとに当たりが 30 以上の候補から下の端がいちばん高い買い方を選び、その中で下の端がいちばん高い券種（docs/03 の 3）。型は ◎ランク/配当率の等級。")
    (OUT / "選んだ券種.json").write_text(json.dumps([{"cell": cell, "ticket": item.ticket, "choice": item.choice.__dict__}
                                                   for cell, item in zip(CELLS, chosen, strict=True)], ensure_ascii=False, indent=1), encoding="utf-8")
    render.write(render.render([table], "markdown"), OUT / "選んだ券種.md", fmt="markdown")
    print(f"保存先: {OUT / '選んだ券種.md'}", file=sys.stderr)


def _check(args: argparse.Namespace) -> None:
    chosen = [(item["cell"], item["ticket"], CellChoice(**item["choice"])) for item in json.loads((OUT / "選んだ券種.json").read_text(encoding="utf-8"))]
    graded, graded_days = _selected(OUT / "候補", chosen)
    whole, whole_days = _selected(ALL_RACES_OUT / "候補", chosen)
    top_win = _one_formation(OUT / "候補" / "単勝.npz", TOP_WIN)
    marked = pd.read_parquet(MARKED, columns=["race_id", "mark", "place_value", "place_payout"])
    place = PlaceBaseline().build(marked, _cells_table(), CELLS, graded_days)
    rows, tables = [], []
    for name, selected, days in (("型ごとに選んだ券種（重賞）", graded, graded_days), ("◎ の単勝（重賞）", top_win, graded_days),
                                 ("前の複勝2点（重賞）", place, graded_days), ("参考: 型ごとに選んだ券種（全レース）", whole, whole_days)):
        summary_of = ChoiceSummary(days)
        mask = np.array([day.year in CONFIRM_YEARS for day in days])
        summary = summary_of.summary(selected, mask)
        yearly = summary_of.yearly(selected)
        yearly = yearly[yearly["年"].isin(CONFIRM_YEARS)]
        rows.append([name, _pct(summary["回収率"]), _pct(summary["下の端"]), _pct(summary["的中率"]), f"{int((yearly['回収率'] > 1.0).sum())}/{len(yearly)}",
                     f"{summary['レース']:,.0f}", f"{summary['1レースの点数']:.1f}"])
        if name.startswith("型ごと"):
            tables.append(Table(["年", "回収率", "的中率", "レース"], [[int(row["年"]), _pct(row["回収率"]), _pct(row["的中率"]), f"{row['レース']:,.0f}"]
                                                              for _, row in yearly.iterrows()], title=f"{name}: 年ごと"))
    graded_mask = np.array([day.year in CONFIRM_YEARS for day in graded_days])
    by_cell = []
    for index, (cell, ticket, choice) in enumerate(chosen):
        one = graded[index][graded_mask]
        stake, payout, races, hits = one[:, POINTS].sum() * 100, one[:, PAYOUT].sum(), one[:, RACES].sum(), one[:, HIT_RACES].sum()
        by_cell.append([cell, ticket, choice.label, f"{races:,.0f}", _pct(payout / stake if stake else np.nan), _pct(hits / races if races else np.nan)])
    by_ticket = []
    for ticket in TICKET_LABELS:
        rows_of = [index for index, (_, name, _) in enumerate(chosen) if name == ticket]
        if not rows_of:
            continue
        one = graded[rows_of][:, graded_mask].sum(axis=0)
        stake, payout, races, hits = one[:, POINTS].sum() * 100, one[:, PAYOUT].sum(), one[:, RACES].sum(), one[:, HIT_RACES].sum()
        by_ticket.append([ticket, f"{races:,.0f}", _pct(payout / stake if stake else np.nan), _pct(hits / races if races else np.nan)])
    passed = _number(rows[0][1]) > 100.0 and _number(rows[0][1]) > _number(rows[1][1])
    tables = [Table(["買い方", "回収率", "下の端", "的中率", "100% 超えの年", "レース", "1レースの点数"], rows,
                    title=f"結果（{CONFIRM_YEARS.start}〜{CONFIRM_YEARS.stop - 1}年。1点 100円・確定オッズ）",
                    note=f"採用の線（docs/03 の 5: 重賞で 100% 超え、かつ ◎ の単勝より高い）: {'満たす' if passed else '満たさない'}。"),
              Table(["券種", "重賞", "回収率", "的中率"], by_ticket, title="券種ごと（重賞・確かめる期間）"),
              Table(["型", "券種", "買い方", "重賞", "回収率", "的中率"], by_cell, title="型ごと（重賞・確かめる期間）"), *tables]
    render.write(render.render(tables, "markdown"), OUT / "確かめ.md", fmt="markdown")
    print(f"保存先: {OUT / '確かめ.md'}\n採用の線: {'満たす' if passed else '満たさない'}", file=sys.stderr)


def _selected(folder: Path, chosen: list[tuple[str, str, CellChoice]]) -> tuple[np.ndarray, list[pd.Timestamp]]:
    """型ごとに選んだ券種と買い方の行だけを集めた配列 [セル, 開催日, 4] と開催日（候補は名前で引く）。"""
    rows, days = [], None
    for cell_index, (cell, ticket, choice) in enumerate(chosen):
        values, cells, ticket_days, labels = CandidateCounter.load(folder / f"{ticket}.npz")
        if cells[cell_index] != cell:
            raise ValueError("セルの並びが合っていません")
        if days is not None and ticket_days != days:
            raise ValueError("券種ごとの開催日の並びが合っていません")
        days = ticket_days
        rows.append(values[labels.index(choice.label), cell_index])
    return np.stack(rows, axis=0), days


def _one_formation(path: Path, label: str) -> np.ndarray:
    values, _, _, labels = CandidateCounter.load(path)
    return values[labels.index(label)]


def _pct(value: float) -> str:
    return "―" if value is None or not np.isfinite(value) else f"{value:.1%}"


def _number(text: str) -> float:
    return float(text.rstrip("%")) if text.endswith("%") else float("nan")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("count", help="重賞だけで、型ごとに 8券種の候補を数え上げる")
    subparsers.add_parser("pick", help="全レースの 2015〜2020年で、型ごとに券種と買い方を1つ選ぶ")
    subparsers.add_parser("check", help="重賞の 2021〜2026年で一度だけ数える")
    return parser


if __name__ == "__main__":
    main()
