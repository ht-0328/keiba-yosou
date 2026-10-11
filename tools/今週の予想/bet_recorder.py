"""買うレースの計画を、買い目の記録（回顧の表1）に書く。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.review import ReviewStore, names
from yosou.shared.betting import TicketType

from 今週の予想.race_plan import NO_BET, RacePlan


class BetRecorder:
    """計画（``DayPlanner.plan``）の複勝の買い目を、表1「買い目の記録」に書く（買い目を決めたときに書き、レースのあとに払戻を書き足す）。

    同じレースの未精算の行は書き直す（前日の計画を当日に作り直したときに、古い買い目を残さない）。
    記録だけの行は作らない（今の決まりで買わない券種は記録もしない）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def record(self, plans: list[RacePlan], odds_at: str) -> int:
        rows = []
        for plan in plans:
            self._store.delete(names.BETS_TABLE, f"{names.RACE_ID} = ? AND NOT {names.SETTLED}", [plan.rid])
            if plan.kind == NO_BET:
                continue
            for pick in plan.picks:
                rows.append({
                    names.RACE_ID: plan.rid, names.TICKET_TYPE: TicketType.PLACE.label, names.COMBO: f"{pick.horse_no:02d}",
                    names.RACE_DATE: date(int(plan.rid[:4]), int(plan.rid[4:6]), int(plan.rid[6:8])), names.PARTICIPATION: plan.kind,
                    names.RECORD_ONLY: False, names.STAKE_YEN: pick.yen, names.BOUGHT_PROBABILITY: pick.probability, names.BOUGHT_VALUE: pick.value,
                    names.BOUGHT_ODDS: pick.odds, names.ODDS_AT: odds_at, names.PAYOUT_YEN: None, names.SETTLED: False,
                })
        return self._store.write(names.BETS_TABLE, pd.DataFrame(rows)) if rows else 0
