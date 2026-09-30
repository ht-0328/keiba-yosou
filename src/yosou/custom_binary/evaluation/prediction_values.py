"""予測した1レースの、期待値とその材料。"""

import numpy as np
import pandas as pd

from yosou.shared.feature.value_types import as_numbers
from yosou.shared.place_value import PlacePriceEstimator

from ..dataset.dataset_columns import MARKET_FIELD_SIZE, MARKET_WHOLE_FIELD
from .payback_rules import FULL_PLACE_FIELD


class PredictionValues:
    """学習の評価（``ExpectedValue``）と同じ計算を、その時点のオッズで行う。

    ``market`` は ``CustomDataset.prediction()`` が作る表（単勝オッズ・複勝オッズ（最低）・出走頭数・全頭が対象）。
    """

    def of(self, probability: np.ndarray, target: str, market: pd.DataFrame,
           place_price: PlacePriceEstimator | None) -> pd.DataFrame:
        win = as_numbers(market["単勝オッズ"]).to_numpy()
        if target == "勝利":
            return pd.DataFrame({"単勝オッズ": win, "期待値": probability * win}, index=market.index)
        coming = 1 - probability if target == "馬券外" else probability
        field = int(market[MARKET_FIELD_SIZE].iloc[0])
        if bool(market[MARKET_WHOLE_FIELD].iloc[0]) and coming.sum() > 0:
            places = 3.0 if field >= FULL_PLACE_FIELD else 2.0
            coming = np.clip(coming * places / coming.sum(), 0.0, 1.0)
        lowest = as_numbers(market["複勝オッズ（最低）"])
        price = lowest if place_price is None else place_price.estimate(lowest)
        return pd.DataFrame({
            "単勝オッズ": win, "複勝オッズ（最低）": lowest.to_numpy(), "3着以内の確率": coming,
            "想定払戻倍率": price.to_numpy(), "期待値": coming * price.to_numpy(),
        }, index=market.index)
