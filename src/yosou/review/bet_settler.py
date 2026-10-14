"""買い目の記録（表1）の未精算の行に、終わったレースの払戻を書き足す。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO, YEN

from . import names
from .repository import ReviewStore

#: 1頭を当てる券種（払戻は事実表の馬ごとの払戻から）。ほかは組の券種（払戻の明細から）。
_SINGLE_HORSE_TICKETS = (TicketType.PLACE, TicketType.WIN)


class BetSettler:
    """表1の未精算の買い目のうち、レースが終わったもの（``runs`` に成績がある）に払戻を書き、精算済みにする。

    今の決まりで買うのは、複勝と、当日の期待度「高」のレースの単勝・馬単。複勝・単勝の払戻は事実表の馬ごとの払戻（100円あたり。当たらなければ 0）、
    馬単のような組の券種の払戻は、``con`` を渡したときに払戻の明細（``PayoutRepository``）から読み、金額 ÷ 100 を掛けて円にする。
    組の券種は、レースが終わっていて組の馬が全部走っていれば明細の払戻（無ければ外れで 0）、組の馬に取消・除外がいれば返還（金額をそのまま戻す）。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def settle(self, runs: pd.DataFrame, con: duckdb.DuckDBPyConnection | None = None) -> int:
        """精算した買い目の数。"""
        pending = self._store.read(names.BETS_TABLE, f"NOT {names.SETTLED}")
        if pending.empty:
            return 0
        by_key = self._payouts_by_horse(runs)
        combos = self._combo_payouts(con, pending) if con is not None else {}
        paid = {(label, rid) for label, rid, _ in combos}
        # 組の券種は、払戻の明細を読めるとき（con があるとき）だけ精算する
        combo_races = set(by_key.index.get_level_values(0)) if con is not None else set()
        rows = [self._settled_row(bet, by_key, combo_races, combos, paid) for _, bet in pending.iterrows()]
        settled = [row for row in rows if row is not None]
        return self._store.write(names.BETS_TABLE, pd.DataFrame(settled)) if settled else 0

    def _payouts_by_horse(self, runs: pd.DataFrame) -> pd.DataFrame:
        """終わった出走の行を、（レースID, 2桁の馬番）で引ける形にしたもの。"""
        finished = runs[runs["finish"].notna() | runs["win_payout"].notna()]
        horse_no = pd.to_numeric(finished["horse_no"], errors="coerce").astype("Int64").astype(str).str.zfill(2)
        return finished.set_index([finished["race_id"].astype(str), horse_no])

    def _settled_row(self, bet: pd.Series, by_key: pd.DataFrame, combo_races: set[str],
                     combos: dict[tuple[str, str, str], float], paid: set[tuple[str, str]]) -> dict | None:
        """1点を精算した行。レースが終わっていない・払戻がまだ無ければ None。"""
        ticket_type = TicketType.parse(str(bet[names.TICKET_TYPE]))
        key = (str(bet[names.RACE_ID]), str(bet[names.COMBO]))
        if ticket_type in _SINGLE_HORSE_TICKETS:
            return self._single_row(bet, ticket_type, key, by_key)
        if key[0] not in combo_races:
            return None
        return self._combo_row(bet, ticket_type, key, by_key, combos, paid)

    def _single_row(self, bet: pd.Series, ticket_type: TicketType, key: tuple[str, str], by_key: pd.DataFrame) -> dict | None:
        """複勝・単勝の1点を精算した行（事実表の馬ごとの 100円あたりの払戻から）。レースが終わっていなければ None。"""
        if key not in by_key.index:
            return None
        column = "place_payout" if ticket_type is TicketType.PLACE else "win_payout"
        per_100 = pd.to_numeric(by_key.loc[key, column], errors="coerce")
        if pd.isna(per_100):
            return None
        return self._settled(bet, float(per_100) * float(bet[names.STAKE_YEN]) / 100.0)

    def _combo_row(self, bet: pd.Series, ticket_type: TicketType, key: tuple[str, str], by_key: pd.DataFrame,
                   combos: dict[tuple[str, str, str], float], paid: set[tuple[str, str]]) -> dict | None:
        """組の券種の1点を精算した行。組の馬が全部走っていれば明細の払戻（その券種の払戻がまだ取り込まれていなければ精算しない）、
        取消・除外がいれば返還。"""
        rid, combo = key
        horses = [combo[at:at + 2] for at in range(0, len(combo), 2)]
        stake = float(bet[names.STAKE_YEN])
        if not all((rid, horse) in by_key.index for horse in horses):
            return self._settled(bet, stake)
        if (ticket_type.label, rid) not in paid:
            return None
        return self._settled(bet, combos.get((ticket_type.label, rid, combo), 0.0) * stake / 100.0)

    def _settled(self, bet: pd.Series, yen: float) -> dict:
        """買い目の行に、払戻（円。四捨五入）と精算済みを書いたもの。"""
        return {**bet.to_dict(), names.PAYOUT_YEN: int(round(yen)), names.SETTLED: True}

    def _combo_payouts(self, con: duckdb.DuckDBPyConnection, pending: pd.DataFrame) -> dict[tuple[str, str, str], float]:
        """（券種, レース, 組番）→ 100円あたりの払戻。未精算の組の券種の開催日の範囲だけ読む。同着で払戻が複数ある組は足す。"""
        combo_bets = pending[~pending[names.TICKET_TYPE].isin([ticket_type.label for ticket_type in _SINGLE_HORSE_TICKETS])]
        found: dict[tuple[str, str, str], float] = {}
        for label, group in combo_bets.groupby(names.TICKET_TYPE, sort=False):
            found.update(self._payouts_of(con, TicketType.parse(str(label)), group))
        return found

    def _payouts_of(self, con: duckdb.DuckDBPyConnection, ticket_type: TicketType, group: pd.DataFrame) -> dict[tuple[str, str, str], float]:
        """1つの券種の、未精算の買い目の開催日の範囲の払戻の明細（（券種, レース, 組番）→ 100円あたりの払戻）。"""
        days = pd.to_datetime(group[names.RACE_DATE])
        rows = PayoutRepository(con, ticket_type).read(RaceDayRange(_day(days.min()), _day(days.max())))
        summed = rows.groupby(["race_id", COMBO])[YEN].sum()
        return {(ticket_type.label, str(rid), str(combo)): float(yen) for (rid, combo), yen in summed.items()}


def _day(value: pd.Timestamp) -> date:
    return value.date()
