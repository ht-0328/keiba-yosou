"""研究「重賞の買い方」の入口: 重賞だけで型の候補を数え上げ、◎ランクごとに選び、2021〜2026年で確かめる（docs/01 の手順2〜5）。

    uv run python research/重賞の買い方/stakes_bets.py races     # 手順2: 重賞のレースの一覧を元DB から読む（重賞.parquet）
    uv run python research/重賞の買い方/stakes_bets.py count     # 手順3: 8券種の型の候補を重賞だけで数え上げる（候補/<券種>.npz）
    uv run python research/重賞の買い方/stakes_bets.py select    # 手順4: 2015〜2020年で ◎ランクごとに型を選ぶ（選んだ型.md・.json）
    uv run python research/重賞の買い方/stakes_bets.py confirm   # 手順5: 2つの案を 2021〜2026年で一度だけ数える（確かめ.md）

先に研究「全レース全券種の買い方」の材料（``等級.parquet``・``枠番.parquet``）と、研究「複勝以外の回収率100超」の表が要る。
出るものは全部 Git 対象外の ``reports/重賞の買い方/``。
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

from 共通 import db, render, stakes  # noqa: E402
from 共通.render import Table  # noqa: E402

from 全レース全券種の買い方.analysis.candidate_counter import CandidateCounter  # noqa: E402
from 全レース全券種の買い方.analysis.cell_selector import CellChoice, CellSelector  # noqa: E402
from 全レース全券種の買い方.analysis.choice_summary import ChoiceSummary  # noqa: E402
from 全レース全券種の買い方.analysis.combos_source import BRACKET_LABEL, TICKET_LABELS  # noqa: E402
from 全レース全券種の買い方.analysis.formation import MAX_POINTS, candidates  # noqa: E402
from 全レース全券種の買い方.analysis.horse_slots import HorseSlots  # noqa: E402
from 全レース全券種の買い方.formations import _source  # noqa: E402
from 全レース全券種の買い方.materials import MARKED, OUT as ALL_RACES_OUT  # noqa: E402
from 重賞の買い方.analysis import RANKS, GradedCells, PlaceBaseline, WinningTickets  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "reports" / "重賞の買い方"
GRADED = OUT / "重賞.parquet"
#: 選ぶ期間と確かめる期間（docs/01 の 4・6）。
SELECT_YEARS = range(2015, 2021)
CONFIRM_YEARS = range(2021, 2027)
ALL_YEARS = range(2015, 2027)
#: 当たったレースの下限（docs/01 の 4）。
MIN_HITS = 15
#: 2つの案の名前（docs/01 の 5）。
ALL_TICKETS, WINNERS = "案1 全券種", "案2 勝てる券種"
BASELINE = "比べる相手（今の複勝2点）"


def main() -> None:
    args = _parser().parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"races": _races, "count": _count, "select": _select, "confirm": _confirm}[args.command](args)


def _races(args: argparse.Namespace) -> None:
    with db.open_db(args.db, default=db.JRA) as con:
        frame = con.execute(f"SELECT race_id, CAST(race_date AS VARCHAR) AS race_date, grade FROM ({stakes.stakes_map_sql()})").df()
    frame["grade"] = frame["grade"].map(stakes.GRADE_NAMES)
    frame.to_parquet(GRADED, index=False)
    print(f"保存先: {GRADED}（{len(frame):,} レース）\n{frame['grade'].value_counts().sort_index().to_string()}", file=sys.stderr)


def _cells_table() -> pd.DataFrame:
    grades = pd.read_parquet(ALL_RACES_OUT / "等級.parquet")
    return GradedCells().build(grades, pd.read_parquet(GRADED))


def _days(cells_table: pd.DataFrame) -> list[pd.Timestamp]:
    return sorted(pd.to_datetime(cells_table["race_date"]).drop_duplicates())


def _count(args: argparse.Namespace) -> None:
    marked = pd.read_parquet(MARKED)
    cells_table = _cells_table()
    print(f"重賞 {len(cells_table):,} レース（◎ランクごと: {cells_table['cell'].value_counts().sort_index().to_dict()}）", file=sys.stderr, flush=True)
    source = _source(marked, HorseSlots().build(marked), cells_table)
    days = _days(cells_table)
    for label in ([args.ticket] if args.ticket else TICKET_LABELS):
        formations = [formation for formation in candidates(label) if formation.max_points == MAX_POINTS]
        print(f"{label}: 候補 {len(formations)} 個を数えます", file=sys.stderr, flush=True)
        counter = CandidateCounter(source, label, formations, RANKS, days)
        counter.count([year for year in ALL_YEARS if not (label == BRACKET_LABEL and year == 2015)])
        print(f"  保存: {counter.save(OUT / '候補' / f'{label}.npz')}", file=sys.stderr, flush=True)


def _select(args: argparse.Namespace) -> None:
    chosen: dict[str, list[dict[str, object]]] = {}
    choices_by_ticket: dict[str, list[CellChoice]] = {}
    tables: list[Table] = []
    for label in TICKET_LABELS:
        values, cells, days, labels = CandidateCounter.load(OUT / "候補" / f"{label}.npz")
        day_mask = np.array([day.year in SELECT_YEARS for day in days])
        selector = CellSelector(labels, cells, min_hits=MIN_HITS)
        choices = selector.select(values, day_mask)
        selector.table(values, day_mask).to_csv(OUT / "候補" / f"{label}-成績.csv", index=False, encoding="utf-8-sig")
        choices_by_ticket[label] = choices
        chosen[label] = [choice.__dict__ for choice in choices]
        tables.append(Table(["◎ランク", "選んだ型", "回収率", "下の端", "当たったレース", "レース", "1レースの点数", "注意"],
                            [[choice.cell, choice.label, _pct(choice.recovery), _pct(choice.lower), choice.hits, choice.races,
                              f"{choice.points_per_race:.1f}", "" if choice.enough else "当たり不足"] for choice in choices],
                            title=f"{label}: ◎ランクごとに選んだ型（{SELECT_YEARS.start}〜{SELECT_YEARS.stop - 1}年の重賞）",
                            note=f"当たったレースが {MIN_HITS} 以上の候補のうち、回収率の 90% の幅の下の端がいちばん高い型。「当たり不足」は、足りる候補が無く全候補から選んだもの。"))
    winners = WinningTickets().choose(choices_by_ticket, TICKET_LABELS, RANKS)
    tables.insert(0, Table(["◎ランク", "案2 で買う券種"], [[cell, "・".join(winners[cell]) or "―"] for cell in RANKS],
                           title="案2（勝てる券種）で買う券種",
                           note="選ぶ期間の回収率が 100% 以上の券種。1つも無いセルは、下の端がいちばん高い券種を1つ（docs/01 の 5）。"))
    (OUT / "選んだ型.json").write_text(json.dumps({"choices": chosen, "winners": winners}, ensure_ascii=False, indent=1), encoding="utf-8")
    path = OUT / "選んだ型.md"
    render.write(render.render(tables, "markdown"), path, fmt="markdown")
    print(f"保存先: {path}", file=sys.stderr)


def _confirm(args: argparse.Namespace) -> None:
    saved = json.loads((OUT / "選んだ型.json").read_text(encoding="utf-8"))
    winners: dict[str, list[str]] = saved["winners"]
    per_ticket: dict[str, np.ndarray] = {}
    days: list[pd.Timestamp] = []
    cells: list[str] = []
    for label in TICKET_LABELS:
        values, cells, ticket_days, _ = CandidateCounter.load(OUT / "候補" / f"{label}.npz")
        days = days or ticket_days
        if ticket_days != days:
            raise ValueError("券種ごとの開催日の並びが合っていません")
        per_ticket[label] = ChoiceSummary.selected(values, [CellChoice(**choice) for choice in saved["choices"][label]])
    summary_of = ChoiceSummary(days)
    confirm_mask = np.array([day.year in CONFIRM_YEARS for day in days])
    plans = {
        ALL_TICKETS: sum(per_ticket.values()),
        WINNERS: sum(per_ticket[label] * np.array([label in winners[cell] for cell in cells], dtype=float)[:, None, None] for label in TICKET_LABELS),
    }
    marked = pd.read_parquet(MARKED, columns=["race_id", "mark", "place_value", "place_payout"])
    baseline = PlaceBaseline().build(marked, _cells_table(), cells, days)
    rows, yearly_tables = [], []
    for name, selected in (*plans.items(), (BASELINE, baseline)):
        summary = summary_of.summary(selected, confirm_mask)
        yearly = summary_of.yearly(selected)
        yearly = yearly[yearly["年"].isin(CONFIRM_YEARS)]
        over = int((yearly["回収率"] > 1.0).sum())
        rows.append([name, _pct(summary["回収率"]), _pct(summary["下の端"]), f"{over}/{len(yearly)}", f"{summary['レース']:,.0f}",
                     f"{summary['1レースの点数']:.1f}", f"{summary['投資']:,.0f}円", f"{summary['払戻']:,.0f}円"])
        by_rank = summary_of.by_cell(selected, cells, [CellChoice(cell, 0, name, 0, 0, 0, 0, 0, True) for cell in cells], confirm_mask)
        yearly_tables.append(Table(["年", "回収率", "下の端", "レース", "1レースの点数"],
                                   [[int(row["年"]), _pct(row["回収率"]), _pct(row["下の端"]), f"{row['レース']:,.0f}", f"{row['1レースの点数']:.1f}"]
                                    for _, row in yearly.iterrows()], title=f"{name}: 年ごと"))
        yearly_tables.append(Table(["◎ランク", "回収率", "下の端", "レース", "1レースの点数"],
                                   [[row["セル"], _pct(row["回収率"]), _pct(row["下の端"]), f"{row['レース']:,.0f}", f"{row['1レースの点数']:.1f}"]
                                    for _, row in by_rank.iterrows()], title=f"{name}: ◎ランクごと"))
    better = max(plans, key=lambda name: summary_of.summary(plans[name], confirm_mask)["回収率"])
    tables = [Table(["案", "回収率", "下の端", "100% 超えの年", "レース", "1レースの点数", "投資", "払戻"], rows,
                    title=f"案ごとの結果（{CONFIRM_YEARS.start}〜{CONFIRM_YEARS.stop - 1}年の重賞。1点 100円）",
                    note=f"本番に入れる案（docs/01 の 6: 合計の回収率が高いほう）: {better}。「レース」は案の買い目が1つでもある重賞の数を券種ごとに足したもの（券種の数だけ重なる）。"
                         "確定オッズでの検証なので、実際に買うときより良く出る。"),
              _ticket_table(per_ticket, winners, cells, summary_of, confirm_mask, days), *yearly_tables]
    path = OUT / "確かめ.md"
    render.write(render.render(tables, "markdown"), path, fmt="markdown")
    print(f"保存先: {path}\n本番に入れる案: {better}", file=sys.stderr)


def _ticket_table(per_ticket: dict[str, np.ndarray], winners: dict[str, list[str]], cells: list[str], summary_of: ChoiceSummary,
                  confirm_mask: np.ndarray, days: list[pd.Timestamp]) -> Table:
    rows = []
    for label, selected in per_ticket.items():
        summary = summary_of.summary(selected, confirm_mask)
        yearly = summary_of.yearly(selected)
        yearly = yearly[yearly["年"].isin(CONFIRM_YEARS)]
        in_winners = "・".join(cell for cell in cells if label in winners[cell]) or "―"
        rows.append([label, _pct(summary["回収率"]), _pct(summary["下の端"]), _pct(summary["的中率"]), f"{int((yearly['回収率'] > 1.0).sum())}/{len(yearly)}",
                     f"{summary['レース']:,.0f}", f"{summary['1レースの点数']:.1f}", in_winners])
    return Table(["券種", "回収率", "下の端", "的中率", "100% 超えの年", "レース", "1レースの点数", "案2 で買う ◎ランク"], rows,
                 title="券種ごとの結果（案1 の型。確かめる期間）", note="的中率は、その券種で当たったレース ÷ 買ったレース。")


def _pct(value: float) -> str:
    return "―" if value is None or not np.isfinite(value) else f"{value:.1%}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    parser.add_argument("--db", type=Path, default=None, help="元DB のパス（既定: ../jvdata-store/jvdata.duckdb か環境変数 YOSOU_DB）")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("races", help="重賞のレースの一覧を元DB から読む")
    count = subparsers.add_parser("count", help="8券種の型の候補を重賞だけで数え上げる")
    count.add_argument("--ticket", choices=TICKET_LABELS, default=None, help="1券種だけ数える")
    subparsers.add_parser("select", help="2015〜2020年で ◎ランクごとに型を選ぶ")
    subparsers.add_parser("confirm", help="2つの案を 2021〜2026年で一度だけ数える")
    return parser


if __name__ == "__main__":
    main()
