"""買い目の記録（表1）の未精算の行に、終わったレースの払戻を書き足す。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO, YEN

from . import names
from .review_store import ReviewStore


class BetSettler:
    """表1の未精算の買い目のうち、レースが終わったもの（``runs`` に成績がある）に払戻を書き、精算済みにする。

    今の決まりで買うのは、複勝と、当日の期待度「高」のレースの単勝・馬単。複勝・単勝の払戻は事実表の馬ごとの払戻（100円あたり。当たらなければ 0）、
    馬単のような組の券種の払戻は、``con`` を渡したときに払戻の明細（``PayoutRepository``）から読み、金額 ÷ 100 を掛けて円にする。
    組の券種は、レースが終わっていて組の馬が全部走っていれば明細の払戻（無ければ外れで 0）、組の馬に取消・除外がいれば返還（金額をそのまま戻す）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def settle(self, runs: pd.DataFrame, con: duckdb.DuckDBPyConnection | None = None) -> int:
        pending = self._store.read(names.BETS_TABLE, f"NOT {names.SETTLED}")
        if pending.empty:
            return 0
        finished = runs[runs["finish"].notna() | runs["win_payout"].notna()]
        payouts = finished.assign(_horse_no=pd.to_numeric(finished["horse_no"], errors="coerce").astype("Int64").astype(str).str.zfill(2))
        by_key = payouts.set_index([payouts["race_id"].astype(str), payouts["_horse_no"]])
        races = set(payouts["race_id"].astype(str))
        combos = self._combo_payouts(con, pending) if con is not None else {}
        paid = {(label, rid) for label, rid, _ in combos}
        rows = []
        for _, bet in pending.iterrows():
            ticket_type = TicketType.parse(str(bet[names.TICKET_TYPE]))
            key = (str(bet[names.RACE_ID]), str(bet[names.COMBO]))
            if ticket_type not in (TicketType.PLACE, TicketType.WIN):
                row = self._combo_row(bet, ticket_type, key, by_key, combos, paid) if con is not None and key[0] in races else None
                if row is not None:
                    rows.append(row)
                continue
            if key not in by_key.index:
                continue
            column = "place_payout" if ticket_type is TicketType.PLACE else "win_payout"
            per_100 = pd.to_numeric(by_key.loc[key, column], errors="coerce")
            if pd.isna(per_100):
                continue
            rows.append({**bet.to_dict(), names.PAYOUT_YEN: int(round(float(per_100) * float(bet[names.STAKE_YEN]) / 100.0)), names.SETTLED: True})
        return self._store.write(names.BETS_TABLE, pd.DataFrame(rows)) if rows else 0

    def _combo_row(self, bet: pd.Series, ticket_type: TicketType, key: tuple[str, str], by_key: pd.DataFrame,
                   combos: dict[tuple[str, str, str], float], paid: set[tuple[str, str]]) -> dict | None:
        """組の券種の1点を精算した行。組の馬が全部走っていれば明細の払戻（その券種の払戻がまだ取り込まれていなければ精算しない）、
        取消・除外がいれば返還。"""
        rid, combo = key
        horses = [combo[at:at + 2] for at in range(0, len(combo), 2)]
        stake = float(bet[names.STAKE_YEN])
        if all((rid, horse) in by_key.index for horse in horses):
            if (ticket_type.label, rid) not in paid:
                return None
            yen = combos.get((ticket_type.label, rid, combo), 0.0) * stake / 100.0
        else:
            yen = stake
        return {**bet.to_dict(), names.PAYOUT_YEN: int(round(yen)), names.SETTLED: True}

    def _combo_payouts(self, con: duckdb.DuckDBPyConnection, pending: pd.DataFrame) -> dict[tuple[str, str, str], float]:
        """（券種, レース, 組番）→ 100円あたりの払戻。未精算の組の券種の開催日の範囲だけ読む。同着で払戻が複数ある組は足す。"""
        found: dict[tuple[str, str, str], float] = {}
        for label, group in pending.groupby(names.TICKET_TYPE, sort=False):
            ticket_type = TicketType.parse(str(label))
            if ticket_type in (TicketType.PLACE, TicketType.WIN):
                continue
            days = pd.to_datetime(group[names.RACE_DATE])
            rows = PayoutRepository(con, ticket_type).read(RaceDayRange(_day(days.min()), _day(days.max())))
            for (rid, combo), yen in rows.groupby(["race_id", COMBO])[YEN].sum().items():
                found[(ticket_type.label, str(rid), str(combo))] = float(yen)
        return found


def _day(value: pd.Timestamp) -> date:
    return value.date()
