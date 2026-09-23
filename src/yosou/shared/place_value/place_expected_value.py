"""複勝を買う期待値を出す。"""

from __future__ import annotations

import pandas as pd

from ..dataset.column_names import FIELD_SIZE, PLACE_ODDS_LOW
from ..feature.odds import TOP2_RATE, TOP3_RATE
from .place_hit_probability import PlaceHitProbability
from .place_price_estimator import PlacePriceEstimator

#: 出す列の名前（予測の結果の表にも、そのまま出す）。
PLACE_PROBABILITY = "複勝的中の確率"
PLACE_PRICE = "複勝の見込みの倍率"
PLACE_VALUE = "複勝の期待値"


class PlaceExpectedValue:
    """3着以内の確率と、複勝オッズ（最低）・頭数・オッズから見た2着以内率と3着以内率の列から、複勝を買う期待値を出す。

    期待値 = 複勝的中の確率 × 見込みの払戻の倍率（1 で元返し。1.2 なら 100円あたり平均 120円戻る見込み）。
    例: 3着以内の確率 0.25・最低オッズ 4.0倍・その帯の倍率 1.15 なら、0.25 × 4.0 × 1.15 = 1.15。
    複勝オッズの無い馬（締め切り前のオッズを取り込んでいない、木曜）は欠損値。
    """

    def __init__(self, estimator: PlacePriceEstimator) -> None:
        self._estimator = estimator
        self._probability = PlaceHitProbability()

    def of(self, top3: pd.Series, table: pd.DataFrame) -> pd.DataFrame:
        """列は ``PLACE_PROBABILITY``・``PLACE_PRICE``・``PLACE_VALUE``。行の並びと index は ``table`` と同じ。

        ``table`` は、複勝オッズ（最低）・確定の出走頭数・オッズから見た2着以内率・3着以内率の列を持つ表。
        """
        probability = self._probability.of(top3, table[FIELD_SIZE], table[TOP2_RATE], table[TOP3_RATE])
        price = self._estimator.estimate(table[PLACE_ODDS_LOW])
        return pd.DataFrame({PLACE_PROBABILITY: probability, PLACE_PRICE: price, PLACE_VALUE: probability * price},
                            index=table.index)
