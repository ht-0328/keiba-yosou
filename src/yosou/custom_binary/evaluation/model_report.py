"""学習したモデルの、1つの期間での当たり具合と回収率。"""

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import EnsembleModel

from .paybacks import Paybacks
from .place_price_fit import PlacePriceFit
from .probability_scores import ProbabilityScores


class ModelReport:
    """確率の当たり具合（``scores``）と、その確率で買った回収率（``paybacks``）。

    複勝の想定払戻倍率は ``train``（学習期間）の払戻から求める。
    """

    def of(self, ensemble: EnsembleModel, data: TrainingData, target: str, train: TrainingData) -> dict:
        probability = ensemble.predict_proba(data) if len(data) else np.array([])
        place_price = PlacePriceFit().fit(train)
        return {"scores": ProbabilityScores().evaluate(ensemble, data),
                "paybacks": Paybacks().of(data, probability, target, place_price)}
