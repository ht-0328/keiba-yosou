"""研究「裏目を買うかの予想」の、◎ の入った馬単・3連単の組（組の期待値・確定オッズ・払戻）を、期間を決めて集める。

    uv run python research/裏目を買うかの予想/analysis/candidates.py --start 2025-09-06 --end 2026-11-15 [--db <DB>]

印の表（``marked_table.py`` が書いた ``reports/裏目を買うかの予想/marked.pkl``）の、``--start`` 以上 ``--end`` 未満の開催日のレースについて、
馬単・3連単の全部の組の期待値を、今週の予想の印の買い目と同じ部品（``ComboValuePicker`` と ``MARK_VALUE_RULES``。確定オッズの板）で出し、
印（◎○▲△☆）の付いた馬だけで、◎ を含む組に絞って、払戻（道具「印の成績」の ``TicketPayouts``）を付ける。
出るもの（Git 対象外）: ``reports/裏目を買うかの予想/candidates_<start>_<end>.pkl``。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_ROOT / "tools"))

import 印の成績.mark_stats as ms  # noqa: E402
from yosou.shared.betting import TicketType  # noqa: E402
from yosou.shared.repository import ComboBlendWeightsRepository, FinalOddsRepository, RaceDayRange  # noqa: E402
from 今週の予想.combo_value_picker import ComboValuePicker  # noqa: E402
from 今週の予想.ticket_rules import MARK_VALUE_RULES  # noqa: E402
from 共通 import db  # noqa: E402
from 印の成績.ticket_payouts import TicketPayouts  # noqa: E402

OUT = _ROOT / "reports" / "裏目を買うかの予想"
#: 組に入れる印（印の付いた馬だけで組む）。
_MARKS = ("◎", "○", "▲", "△", "☆")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", required=True, help="この開催日（YYYY-MM-DD）から")
    parser.add_argument("--end", required=True, help="この開催日（YYYY-MM-DD）の前まで")
    parser.add_argument("--db", default=None, help="読む DB（既定は元DB）")
    args = parser.parse_args()
    marked = pd.read_pickle(OUT / "marked.pkl")
    marked = marked.assign(race_id=marked["race_id"].astype(str))
    days = pd.to_datetime(marked["race_date"])
    marked = marked[(days >= args.start) & (days < args.end)]
    models = ms.build_parser().parse_args([]).models
    picker = ComboValuePicker(MARK_VALUE_RULES, ComboBlendWeightsRepository(models).load())
    positions = {rule.ticket_type: at for at, rule in enumerate(picker.rules)}
    parts = []
    with db.open_db(args.db, default=db.JRA) as con:
        for month, group in marked.groupby(pd.to_datetime(marked["race_date"]).dt.to_period("M"), sort=True):
            dates = pd.to_datetime(group["race_date"])
            boards = {ticket_type: _board(con, ticket_type, RaceDayRange(dates.min().date(), dates.max().date()), set(group["race_id"]))
                      for ticket_type in picker.needed()}
            found = picker.candidates(group, boards)
            marks = {(race, int(no)): mark for race, no, mark in zip(group["race_id"], group["horse_no"], group["mark"]) if mark in _MARKS}
            race_dates = dict(zip(group["race_id"], dates))
            for ticket_type, size in ((TicketType.EXACTA, 2), (TicketType.TRIFECTA, 3)):
                part = _with_top(found[positions[ticket_type]], marks, ticket_type, size)
                parts.append(part.assign(race_date=part["race_id"].map(race_dates)))
            print(f"{month}: {sum(len(part) for part in parts):,} 組", flush=True)
        combos = pd.concat(parts, ignore_index=True)
        combos = TicketPayouts(con).attach(combos.drop(columns=["odds"]))   # 確定オッズと払戻を付け直す
    path = OUT / f"candidates_{args.start}_{args.end}.pkl"
    combos.to_pickle(path)
    print(f"{len(combos):,} 組を {path} に書いた")


def _board(con, ticket_type: TicketType, days: RaceDayRange, races: set[str]) -> pd.DataFrame:
    board = FinalOddsRepository(con, ticket_type).read(days)
    board = board[board["race_id"].astype(str).isin(races)]
    return pd.DataFrame({"race_id": board["race_id"].astype(str), "combo": board["combo"].astype(str), "odds": board["odds"].astype(float)})


def _with_top(found: pd.DataFrame, marks: dict[tuple[str, int], str], ticket_type: TicketType, size: int) -> pd.DataFrame:
    """印の付いた馬だけの組で、◎ を含むもの。列 ``m1``…に1着・2着・3着の馬の印を付ける。"""
    if found.empty:
        return found
    labelled = found.assign(**{f"m{at + 1}": [marks.get((race, int(no))) for race, no in zip(found["race_id"], found[f"h{at + 1}"])]
                               for at in range(size)})
    columns = [f"m{at + 1}" for at in range(size)]
    kept = labelled[columns].notna().all(axis=1) & (labelled[columns] == "◎").any(axis=1)
    return labelled[kept].assign(ticket_type=ticket_type.label)


if __name__ == "__main__":
    main()
