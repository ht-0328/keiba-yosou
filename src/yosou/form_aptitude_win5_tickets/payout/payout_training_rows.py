"""過去の WIN5 から、配当の見積もりの式を作る当たり組の行（材料と払戻）を作る。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from ..repository.win5_columns import CARRY, INVERSE_SUMS, NO_HIT, PAYOUT, RACE_DATE, SATURDAY, WINNER_ODDS
from .combo_market_probability import ComboMarketProbability
from .payout_features import FEATURE_COLUMNS, PayoutFeatures
from .pool_size_estimate import PoolSizeEstimate

#: 発売票数の見積もりの列の名前。
POOL_ESTIMATE = "発売票数の見積もり"


class PayoutTrainingRows:
    """過去の WIN5 の表（``Win5HistoryRepository``）から、式を作るのに使う当たり組の行を作る（設計書 05 の図1、08 の 2.）。

    的中無の回・払戻の無い行・当たり組の5頭のオッズが欠けている行と、それより前の回が無く発売票数を見積もれない回は入れない。
    各回の発売票数は、その回の確定の値ではなく、その回より前の回から見積もった値を使う（予測のときと同じ作り方。設計書 11 の 8）。
    ``fit-payout`` と、過去の WIN5 での確かめ（道具「印の成績」の ``--win5``。区切りごとに、テスト期間の始まりより前の回だけを渡す）が使う。
    """

    def __init__(self) -> None:
        self._pool_size = PoolSizeEstimate()
        self._market = ComboMarketProbability()
        self._features = PayoutFeatures()

    def of(self, history: pd.DataFrame) -> pd.DataFrame:
        """列は開催日・材料（``FEATURE_COLUMNS``）・払戻。"""
        estimates = self._pool_estimates(history)
        rows = history.assign(**{POOL_ESTIMATE: history[RACE_DATE].map(estimates)})
        market = self._market.of_winners(rows[WINNER_ODDS], rows[INVERSE_SUMS])
        usable = (~rows[NO_HIT].astype(bool)) & (rows[PAYOUT] > 0) & market.notna() & rows[POOL_ESTIMATE].notna()
        kept, kept_market = rows.loc[usable], market.loc[usable]
        features = self._features.of(kept_market.to_numpy(), kept[CARRY].to_numpy(), kept[POOL_ESTIMATE].to_numpy())
        features.index = kept.index
        return pd.concat([kept[[RACE_DATE]], features[list(FEATURE_COLUMNS)], kept[[PAYOUT]]], axis=1)

    def _pool_estimates(self, history: pd.DataFrame) -> dict[str, float | None]:
        """開催日 → その日より前の回から見積もった発売票数（前の回が無ければ None）。"""
        days = history.drop_duplicates(RACE_DATE)
        return {day: self._estimate(history, day, bool(saturday)) for day, saturday in zip(days[RACE_DATE], days[SATURDAY], strict=True)}

    def _estimate(self, history: pd.DataFrame, day: str, saturday: bool) -> float | None:
        try:
            return self._pool_size.of(history, date.fromisoformat(day), saturday)
        except LookupError:
            return None
