"""買うレースの計画を、買い目の記録（回顧の表1）に書く。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.review import ReviewStore, names
from yosou.shared.betting import TicketType

from 今週の予想.race_plan import NO_BET, RacePlan


class BetRecorder:
    """計画（``DayPlanner.plan``）の複勝と単勝・馬単の買い目を、表1「買い目の記録」に書く（買い目を決めたときに書き、レースのあとに払戻を書き足す）。
    単勝・馬単の参加の種類は「勝負（単勝・馬単）」（単勝・馬単用の財布から出す）。

    同じレースの未精算の行は書き直す（前日の計画を当日に作り直したときに、古い買い目を残さない）。
    記録だけの行は作らない（今の決まりで買わない券種は記録もしない）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def record(self, plans: list[RacePlan], odds_at: str) -> int:
        rows = []
        for plan in plans:
            self._store.delete(names.BETS_TABLE, f"{names.RACE_ID} = ? AND NOT {names.SETTLED}", [plan.rid])
            day = date(int(plan.rid[:4]), int(plan.rid[4:6]), int(plan.rid[6:8]))
            if plan.kind != NO_BET:
                rows += [self._row(plan.rid, day, plan.kind, TicketType.PLACE.label, f"{pick.horse_no:02d}", pick.yen, pick.probability,
                                   pick.value, pick.odds, odds_at) for pick in plan.picks]
            rows += [self._row(plan.rid, day, names.MATCH_WIN, ticket.ticket_type, ticket.combo, ticket.yen, None, ticket.value, ticket.odds, odds_at)
                     for ticket in plan.tickets]
        return self._store.write(names.BETS_TABLE, pd.DataFrame(rows)) if rows else 0

    @staticmethod
    def _row(rid: str, day: date, kind: str, ticket_type: str, combo: str, yen: int, probability: float | None, value: float | None,
             odds: float | None, odds_at: str) -> dict:
        return {
            names.RACE_ID: rid, names.TICKET_TYPE: ticket_type, names.COMBO: combo, names.RACE_DATE: day, names.PARTICIPATION: kind,
            names.RECORD_ONLY: False, names.STAKE_YEN: yen, names.BOUGHT_PROBABILITY: probability, names.BOUGHT_VALUE: value,
            names.BOUGHT_ODDS: odds, names.ODDS_AT: odds_at, names.PAYOUT_YEN: None, names.SETTLED: False,
        }
