"""ワイドの見込みの倍率を決めるための、過去の最低オッズと払戻を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.repository import FinalOddsRepository, PayoutRepository, RaceDayRange
from yosou.shared.repository.final_odds_repository import COMBO, ODDS
from yosou.shared.repository.payout_repository import YEN

#: 出力の列の名前。
LOWEST_ODDS, PAYOUT_YEN = "最低オッズ", "払戻"


class WidePriceHistory:
    """期間の全レースの、ワイドの組み合わせごとの最低オッズと払戻（外れは 0）を読む。

    読むのは研究「馬券の買い方の検証」のリポジトリ（確定オッズと払戻。1 SQL = 1クラス）で、ここでは突き合わせるだけ。
    ``PlacePriceEstimator`` に渡して、ワイドの見込みの倍率を決めるのに使う。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, first_day: date, last_day: date) -> pd.DataFrame:
        days = RaceDayRange(first_day, last_day)
        odds = FinalOddsRepository(self._con, TicketType.WIDE).read(days)[["race_id", COMBO, ODDS]]
        payouts = PayoutRepository(self._con, TicketType.WIDE).read(days).groupby(["race_id", COMBO], as_index=False)[YEN].sum()
        merged = odds.merge(payouts, on=["race_id", COMBO], how="left")
        return pd.DataFrame({LOWEST_ODDS: merged[ODDS], PAYOUT_YEN: merged[YEN].fillna(0.0)})
