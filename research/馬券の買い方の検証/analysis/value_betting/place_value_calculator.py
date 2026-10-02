"""穴馬モデルの確率から、複勝の期待値を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.place_value import PlaceHitProbability, PlacePriceEstimator

from . import columns as c


class PlaceValueCalculator:
    """1頭ごとの表に、複勝的中の確率・見込みの倍率・複勝の期待値を足す（設計書 買うレースと買い目を決める 07 の 2）。

    - 複勝的中の確率: 穴馬モデルの「3着以内に入る確率」を、7頭以下のレースでは2着までに直したもの（``PlaceHitProbability``）。
    - 見込みの倍率: 複勝の最低オッズ × 帯ごとの倍率 × 幅の帯の倍率（``PlacePriceEstimator``。区切りごとに ``PlacePriceFitter`` で学んだもの）。
    - 期待値 = 複勝的中の確率 × 見込みの倍率（1 で元返し）。
    穴馬でない馬（穴馬モデルの確率が無い馬）は、複勝的中の確率と期待値が欠損（見込みの倍率は、複勝オッズのあるどの馬にも付く）。
    """

    def __init__(self, estimator: PlacePriceEstimator) -> None:
        self._estimator = estimator
        self._hit = PlaceHitProbability()

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        probability = self._hit.of(runners[c.LONGSHOT_PROB], runners[c.FIELD_SIZE], runners[c.MARKET_TOP2], runners[c.MARKET_TOP3])
        price = self._estimator.estimate(runners[c.PLACE_ODDS], runners[c.PLACE_ODDS_HIGH])
        return runners.assign(**{c.PLACE_PROB: probability, c.PLACE_PRICE: price, c.PLACE_VALUE: probability * price})
