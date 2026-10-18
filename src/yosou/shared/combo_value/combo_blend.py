"""4つのもとに重みを掛けて、組の確率と期待値を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..betting import TicketType
from .combo_blend_features import FEATURE_COLUMNS, WIDE_WINNERS
from .combo_blend_weights import ComboBlendWeights

#: 出す列。組の確率と、組の期待値（確率 × オッズ）。
PROBABILITY, VALUE = "probability", "value"


class ComboBlend:
    """``ComboBlendFeatures.build`` の表に、組の確率と期待値を付ける（設計書「買うレースと買い目を決める」07 の 2）。

    組の確率 = exp(重み · もとの対数) を、レースの組で合計 1（ワイドは 3）にそろえた値（条件付きロジット）。
    期待値 = 組の確率 × オッズ（ワイドは最低オッズ）。
    例（架空）: ある組のもとの重み付きの和が、レースの全部の組の和の 2% にあたり、オッズが 60倍なら、期待値は 0.02 × 60 = 1.2。
    """

    def of(self, ticket_type: TicketType, features: pd.DataFrame, weights: ComboBlendWeights) -> pd.DataFrame:
        score = pd.Series(features[list(FEATURE_COLUMNS)].to_numpy(dtype=float) @ np.asarray(weights.values()), index=features.index)
        race = features["race_id"]
        exponent = np.exp(score - score.groupby(race).transform("max"))
        winners = WIDE_WINNERS if ticket_type is TicketType.WIDE else 1.0
        probability = exponent / exponent.groupby(race).transform("sum") * winners
        return features.assign(**{PROBABILITY: probability, VALUE: probability * features["odds"]})
