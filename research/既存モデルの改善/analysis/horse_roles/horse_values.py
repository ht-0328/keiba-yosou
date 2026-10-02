"""馬ごとの期待値と、人気か穴か・人気馬の危険度を、1頭ごとの表に足す。"""

from __future__ import annotations

import pandas as pd

from yosou.favorites_out_of_top3.dataset import FavoriteRule
from yosou.shared.dataset.column_names import FIELD_SIZE, PLACE_ODDS_LOW, POPULARITY, WIN_ODDS
from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE
from yosou.shared.place_value import PlaceHitProbability, PlacePriceEstimator

from ..combined.horse_columns import BASE_TOP3, FAVORITE_PROBABILITY, FORM_PROBABILITY, WIN_PROBABILITY
from .role_columns import DANGER, PLACE_VALUE, POPULAR, WIN_VALUE


class HorseValues:
    """1頭ごとの表（組み合わせの勝率の列を持つ）に、次の列を足す。

    - 単勝の期待値 = 組み合わせの勝率 × 確定の単勝オッズ。例: 勝率 0.20 で 8.0倍なら 1.6。
    - 複勝の期待値 = 全頭の予想の3着以内の確率を複勝的中の確率に直したもの × 複勝の最低オッズから見積もった払戻の倍率。
    - 人気か（人気馬の予想と同じ範囲。13頭以下は 1〜3番人気、14頭以上は 1〜5番人気）。人気でなければ穴。
    - 人気馬の危険度（人気馬の予想の4着以下の確率 − オッズから見た4着以下の確率）。人気馬でなければ欠損値。
    """

    def __init__(self, place_price: PlacePriceEstimator) -> None:
        self._place_price = place_price

    def build(self, horses: pd.DataFrame) -> pd.DataFrame:
        hit = PlaceHitProbability().of(horses[FORM_PROBABILITY], horses[FIELD_SIZE], horses[TOP2_RATE], horses[TOP3_RATE])
        return horses.assign(**{
            WIN_VALUE: horses[WIN_PROBABILITY] * horses[WIN_ODDS],
            PLACE_VALUE: hit * self._place_price.estimate(horses[PLACE_ODDS_LOW]),
            POPULAR: FavoriteRule().are_favorites(horses[POPULARITY], horses[FIELD_SIZE]).to_numpy(),
            DANGER: horses[FAVORITE_PROBABILITY] - (1.0 - horses[BASE_TOP3]),
        })
