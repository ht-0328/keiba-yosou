"""期間ぶんの確定オッズの板と払戻を、元DB から読む。"""

from __future__ import annotations

from collections.abc import Collection, Sequence

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import FinalOddsRepository, PayoutRepository, RaceDayRange

from ..feature import TICKET_TYPES
from .column_names import COMBO, ODDS, RACE_ID
from .final_market import FinalMarket


class FinalMarketLoader:
    """開催日の範囲の確定オッズの板（5券種）と払戻（表を作る券種）を読む。

    券種ごとに共有のリポジトリ（``FinalOddsRepository``・``PayoutRepository``）を呼ぶだけで、SQL は持たない。
    板は ``race_ids`` のレースだけにする。3連単は1か月で数十万組になるので、呼ぶ側は月ごとに区切って読む。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def load(self, days: RaceDayRange, race_ids: Collection[str], payout_types: Sequence[TicketType]) -> FinalMarket:
        """``payout_types`` は払戻を読む券種（表を作る券種）。板は、ほかの券種の市場の材料に使うので、いつも5券種ぶん読む。"""
        boards = {ticket_type: self._board(ticket_type, days, race_ids) for ticket_type in TICKET_TYPES}
        payouts = {ticket_type: PayoutRepository(self._con, ticket_type).read(days) for ticket_type in payout_types}
        return FinalMarket(boards, payouts)

    def _board(self, ticket_type: TicketType, days: RaceDayRange, race_ids: Collection[str]) -> pd.DataFrame:
        board = FinalOddsRepository(self._con, ticket_type).read(days)
        wanted = board[board[RACE_ID].astype(str).isin(race_ids)]
        return pd.DataFrame({
            RACE_ID: wanted[RACE_ID].astype(str), COMBO: wanted[COMBO].astype(str), ODDS: wanted[ODDS].astype(float),
        }).reset_index(drop=True)
