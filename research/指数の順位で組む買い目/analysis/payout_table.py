"""券種ごとの確定の払戻を元DB から読み、組の数で引ける形にする。"""

from __future__ import annotations

from collections.abc import Iterable

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import PayoutRepository, RaceDayRange
from yosou.shared.repository.payout_repository import COMBO as COMBO_TEXT, YEN

from .ticket_builder import COMBO

#: 100円あたりの払戻（円）。
PAYOUT = "payout"
#: 払戻の表の列。
COLUMNS: tuple[str, ...] = ("race_id", COMBO, PAYOUT)


class PayoutTable:
    """1つの券種の払戻の明細を期間ぶん読み（``PayoutRepository``。道具「印の成績」の精算と同じ部品）、
    予測したレースだけに絞って、（レースID, 組の数）ごとの 100円あたりの払戻にまとめる。同着で払戻が複数ある組は足す。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, ticket: TicketType, days: RaceDayRange, race_ids: Iterable[str]) -> pd.DataFrame:
        rows = PayoutRepository(self._con, ticket).read(days)
        rows = rows[rows["race_id"].astype(str).isin(set(race_ids))]
        summed = rows.groupby(["race_id", COMBO_TEXT], as_index=False)[YEN].sum()
        return pd.DataFrame({
            "race_id": summed["race_id"].astype(str), COMBO: pd.to_numeric(summed[COMBO_TEXT]).astype("int64"),
            PAYOUT: summed[YEN].astype(float),
        })[list(COLUMNS)]
