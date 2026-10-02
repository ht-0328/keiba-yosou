"""レースの中の勝率を学ぶ材料を作る。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from yosou.shared.feature.odds import WIN_RATE

from .horse_columns import FAVORITE_SHIFT, FORM_SHIFT, LONGSHOT_SHIFT

#: 材料の名前（表に出すとき）。1つ目は市場の勝率の log で、重み 1・ほかは 0 が「市場そのまま」。
MARKET = "log(オッズから見た勝率)"
#: オッズの無い馬の、オッズから見た勝率の代わり（ごく小さい値）。
_NO_ODDS_RATE = 1e-4
#: 使える上げ下げの列（予想の組み合わせ方の名前 → 列）。
SHIFT_COLUMNS: dict[str, tuple[str, ...]] = {
    "市場だけ": (),
    "全頭だけ": (FORM_SHIFT,),
    "3つの予想": (FORM_SHIFT, LONGSHOT_SHIFT, FAVORITE_SHIFT),
}


class StrengthFeatures:
    """1頭ごとの表から、``RaceStrengthModel`` に渡す材料の行列を作る。

    1列目は log(オッズから見た勝率)、そのあとに予想の上げ下げの列（``shifts``）を並べる。
    ``shifts`` が空なら市場の勝率だけ（「オッズだけ」の基準）。
    """

    def __init__(self, shifts: Sequence[str]) -> None:
        self._shifts = tuple(shifts)

    @property
    def names(self) -> tuple[str, ...]:
        return (MARKET, *self._shifts)

    def matrix(self, table: pd.DataFrame) -> np.ndarray:
        market = np.log(table[WIN_RATE].fillna(_NO_ODDS_RATE).clip(lower=_NO_ODDS_RATE).to_numpy(dtype="float64"))
        shifts = [table[column].fillna(0.0).to_numpy(dtype="float64") for column in self._shifts]
        return np.column_stack([market, *shifts])
