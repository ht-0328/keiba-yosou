"""買い目の記録（表1）の未精算の行に、終わったレースの払戻を書き足す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType

from . import names
from .review_store import ReviewStore


class BetSettler:
    """表1の未精算の買い目のうち、レースが終わったもの（``runs`` に成績がある）に払戻を書き、精算済みにする。

    今の決まりで買うのは複勝だけ（単勝も記録する形は残す）。払戻は事実表の馬ごとの複勝・単勝の払戻（100円あたり。当たらなければ 0）から、
    金額 ÷ 100 を掛けて円にする。ほかの券種の買い目は精算しない（買わない券種は記録もしない決まり）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def settle(self, runs: pd.DataFrame) -> int:
        pending = self._store.read(names.BETS_TABLE, f"NOT {names.SETTLED}")
        if pending.empty:
            return 0
        finished = runs[runs["finish"].notna() | runs["win_payout"].notna()]
        payouts = finished.assign(_horse_no=pd.to_numeric(finished["horse_no"], errors="coerce").astype("Int64").astype(str).str.zfill(2))
        by_key = payouts.set_index([payouts["race_id"].astype(str), payouts["_horse_no"]])
        rows = []
        for _, bet in pending.iterrows():
            ticket_type = TicketType.parse(str(bet[names.TICKET_TYPE]))
            key = (str(bet[names.RACE_ID]), str(bet[names.COMBO]))
            if ticket_type not in (TicketType.PLACE, TicketType.WIN) or key not in by_key.index:
                continue
            column = "place_payout" if ticket_type is TicketType.PLACE else "win_payout"
            per_100 = pd.to_numeric(by_key.loc[key, column], errors="coerce")
            if pd.isna(per_100):
                continue
            rows.append({**bet.to_dict(), names.PAYOUT_YEN: int(round(float(per_100) * float(bet[names.STAKE_YEN]) / 100.0)), names.SETTLED: True})
        return self._store.write(names.BETS_TABLE, pd.DataFrame(rows)) if rows else 0
