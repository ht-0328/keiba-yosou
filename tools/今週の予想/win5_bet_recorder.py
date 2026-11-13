"""1日の WIN5 の買う計画を、買い目の記録（回顧の表1）に書く。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.review import ReviewStore, names

from 今週の予想.win5_plan import Win5Plan


class Win5BetRecorder:
    """WIN5 の計画（``Win5Planner.plan``）で買うなら、表1「買い目の記録」に1日1行で書く（参加の種類は「ポリシー（WIN5）」、券種は WIN5、
    レース ID は1レース目、買い目はフォーメーションの文字、確率は当たる確率、期待値は日の期待値）。

    同じ開催日の未精算の WIN5 の行は書き直す（予想し直したときに、古い買い目を残さない）。買わない日は書かない（前の行は消す）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def record(self, plan: Win5Plan, odds_at: str) -> int:
        day = date.fromisoformat(plan.race_date)
        self._store.delete(names.BETS_TABLE, f"{names.RACE_DATE} = ? AND {names.TICKET_TYPE} = ? AND NOT {names.SETTLED}",
                           [day, names.WIN5_TICKET])
        if not plan.buys:
            return 0
        row = {
            names.RACE_ID: plan.race_id, names.TICKET_TYPE: names.WIN5_TICKET, names.COMBO: plan.formation, names.RACE_DATE: day,
            names.PARTICIPATION: names.POLICY_WIN5, names.RECORD_ONLY: False, names.STAKE_YEN: plan.stake_yen,
            names.BOUGHT_PROBABILITY: plan.hit_probability, names.BOUGHT_VALUE: plan.expected_value, names.BOUGHT_ODDS: None,
            names.ODDS_AT: odds_at, names.PAYOUT_YEN: None, names.SETTLED: False,
        }
        return self._store.write(names.BETS_TABLE, pd.DataFrame([row]))
