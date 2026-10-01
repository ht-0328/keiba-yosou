"""学習・評価のデータの、1円あたりの払戻の見込み（期待値）。"""

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import PLACE_ODDS_LOW, WIN_ODDS
from yosou.shared.feature.value_types import as_numbers
from yosou.shared.place_value import PlacePriceEstimator

from .place_probability import PlaceProbability


class ExpectedValue:
    """勝利なら確率×単勝オッズ、馬券内・馬券外なら3着以内の確率×複勝の想定払戻倍率。オッズの無い馬は欠損値。

    ``place_price`` が無ければ複勝の最低オッズをそのまま使う。
    """

    def of(self, data: TrainingData, probability: np.ndarray, target: str,
           place_price: PlacePriceEstimator | None = None) -> np.ndarray:
        if target == "勝利":
            return probability * as_numbers(data.evaluation[WIN_ODDS]).to_numpy()
        lowest = as_numbers(data.evaluation[PLACE_ODDS_LOW])
        price = lowest.to_numpy() if place_price is None else place_price.estimate(lowest).to_numpy()
        return PlaceProbability().of(data, probability, target) * price
