"""印を付けるのに使う値（人気馬の危険度・穴馬の複勝の期待値）を、1頭ごとの表に足す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset.column_names import FIELD_SIZE, PLACE_ODDS_LOW
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE
from yosou.shared.place_value import PlaceHitProbability, PlacePriceEstimator

from ..combined.horse_columns import BASE_TOP3, FAVORITE_PROBABILITY, LONGSHOT_PROBABILITY

#: 人気馬の危険度（人気馬の予想の4着以下の確率 − オッズから見た4着以下の確率）。人気馬でなければ欠損値。
DANGER = "人気馬の危険度"
#: 穴馬の複勝の期待値（穴馬の予想の複勝的中の確率 × 見込みの払戻の倍率）。穴馬でなければ欠損値。
LONGSHOT_PLACE_VALUE = "穴馬の複勝の期待値"


class MarkMaterial:
    """1頭ごとの表（``HorseTableBuilder`` の出力）に、印を付けるのに使う2つの値を足す。

    - 人気馬の危険度: 正なら、同じオッズの馬より負けやすいと見ている（消・「◎が危うい」の判定に使う）。
    - 穴馬の複勝の期待値: 穴馬の予想の3着以内の確率を複勝的中の確率に直し、複勝の最低オッズから見積もった
      払戻の倍率を掛けたもの（☆の判定に使う）。
    """

    def __init__(self, place_price: PlacePriceEstimator) -> None:
        self._place_price = place_price

    def build(self, horses: pd.DataFrame) -> pd.DataFrame:
        hit = PlaceHitProbability().of(horses[LONGSHOT_PROBABILITY], horses[FIELD_SIZE], horses[TOP2_RATE], horses[TOP3_RATE])
        price = self._place_price.estimate(horses[PLACE_ODDS_LOW])
        return horses.assign(**{
            DANGER: horses[FAVORITE_PROBABILITY] - (1.0 - horses[BASE_TOP3]),
            LONGSHOT_PLACE_VALUE: hit * price,
        })
