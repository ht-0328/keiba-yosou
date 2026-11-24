"""モデルの当たり具合を、市場の確率と比べる。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import EnsembleModel, ProbabilityModel

from .log_loss import weighted_log_loss

#: 比べる相手の名前。2つのモデルの平均、市場の確率そのまま、当たりの数に合わせて一律に伸び縮みさせた市場の確率。
AVERAGE = "平均"
MARKET = "市場"
SCALED_MARKET = "市場（当たりの数にそろえた）"


class MarketComparison:
    """検証データでの対数損失（行の重みつき）を、モデルごと・2つの平均・市場の確率で出す。

    市場の確率は出発点（``baseline``）を確率に戻した値。市場の確率は控除のぶん合計が合わないので、当たりの数に合うように
    一律に伸び縮みさせた値でも比べる（例: 市場の確率の合計が 90、当たりが 100 なら 100 ÷ 90 倍する）。
    モデルの対数損失が市場より小さければ、市場の確率からの上げ下げが当たっている。
    戻り値は 名前（LightGBM・CatBoost・平均・市場・市場（当たりの数にそろえた））→ 対数損失。
    """

    def losses(self, valid: TrainingData, members: Sequence[ProbabilityModel]) -> dict[str, float]:
        hit = valid.label.to_numpy(dtype=float)
        weight = valid.weight.to_numpy(dtype=float) if valid.weight is not None else np.ones(len(valid))
        ensemble = EnsembleModel(members)
        by_member = ensemble.predict_members(valid)
        market = valid.baseline.probabilities().to_numpy(dtype=float)
        scale = (weight * hit).sum() / (weight * market).sum()
        probabilities = {**by_member, AVERAGE: ensemble.combine(by_member), MARKET: market, SCALED_MARKET: market * scale}
        return {name: weighted_log_loss(hit, values, weight) for name, values in probabilities.items()}
