"""複勝を買う期待値（既存モデルの修正計画の 1・2「馬を選ぶ基準」「3着以内と複勝的中」）。

「来やすさ」（3着以内の確率）と「払戻まで考えて買う価値があるか」（期待値）は違う。ここでは、3着以内の確率を
複勝が当たる確率に直し（``PlaceHitProbability``）、複勝の見込みの払戻の倍率（``PlacePriceEstimator``）を掛けて、
複勝を買う期待値（1 で元返し）にする（``PlaceExpectedValue``）。

| クラス | 仕事 |
|---|---|
| ``PlaceHitProbability`` | 3着以内の確率を、複勝が当たる確率に直す（7頭以下は2着まで） |
| ``PlacePriceEstimator`` | 複勝（ワイド）の見込みの払戻の倍率を、最低オッズから見積もる。帯ごとの倍率を学習期間の払戻で決める |
| ``PlaceExpectedValue`` | 上の2つを掛けて、複勝を買う期待値を出す |
| ``PlaceValueColumns`` | 予測の結果に足す列（オッズから見た3着以内率と、複勝的中の確率・見込みの倍率・期待値）を作る |

見込みの倍率は、学習のときに学習データの期間で決めて、モデルと一緒に保存する（``PlacePriceRepository``）。
"""

from .place_expected_value import PLACE_PROBABILITY, PLACE_PRICE, PLACE_VALUE, PlaceExpectedValue
from .place_hit_probability import PlaceHitProbability
from .place_price_estimator import BANDS, PlacePriceEstimator
from .place_value_columns import PlaceValueColumns

__all__ = [
    "PlaceHitProbability", "PlacePriceEstimator", "PlaceExpectedValue", "PlaceValueColumns", "BANDS",
    "PLACE_PROBABILITY", "PLACE_PRICE", "PLACE_VALUE",
]
