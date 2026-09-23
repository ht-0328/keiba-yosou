"""自信のあるレースの判定。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..column_names import FAVORITE_DANGER, FAVORITE_PROB


class ConfidenceJudge:
    """本命（近走と適性モデルの1位）の確率が ``form_threshold`` 以上、かつ本命の危険確率が ``danger_threshold`` 未満なら自信あり。

    本命が人気馬でない（危険確率が欠損）レースは、既定では自信なし（``unknown_danger_is_confident`` で切り替え）。
    ``scores`` は、毎週の上位 k を選ぶときの順位付けに使う点（危険の条件を満たす本命の確率。満たさなければ欠損）。
    しきい値が None の軸は、その条件を課さない。
    """

    def __init__(self, form_threshold: float | None, danger_threshold: float | None,
                 unknown_danger_is_confident: bool = False) -> None:
        self._form_threshold = form_threshold
        self._danger_threshold = danger_threshold
        self._unknown_is_confident = unknown_danger_is_confident

    def scores(self, races: pd.DataFrame) -> pd.Series:
        return races[FAVORITE_PROB].where(self._danger_is_ok(races), np.nan)

    def is_confident(self, races: pd.DataFrame) -> pd.Series:
        if self._form_threshold is None:
            return pd.Series(False, index=races.index)
        return (self.scores(races) >= self._form_threshold).fillna(False)

    def _danger_is_ok(self, races: pd.DataFrame) -> pd.Series:
        danger = races[FAVORITE_DANGER]
        if self._danger_threshold is None:
            return pd.Series(True, index=races.index)
        known_ok = (danger < self._danger_threshold).fillna(False)
        return known_ok | (danger.isna() & self._unknown_is_confident)
