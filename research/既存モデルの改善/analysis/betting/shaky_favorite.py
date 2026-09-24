"""「◎が危うい」（押さえを買う）レースを決める。"""

from __future__ import annotations

import pandas as pd

from .race_columns import HONMEI_DANGER, HONMEI_TOP3


class ShakyFavorite:
    """次のどちらかに当てはまるレースを「◎が危うい」とする（押さえの買い目を足す）。

    - ◎の3着以内の確率が ``line`` より低い（抜けた馬がいない混戦）。``line`` が 0 なら、この条件は使わない。
    - ◎が人気馬で、人気馬の危険度が正（オッズの見立てより負けやすいと見ている）。

    ``line`` は検証期間で決める。
    """

    def __init__(self, line: float) -> None:
        self._line = line

    @property
    def line(self) -> float:
        return self._line

    def of(self, races: pd.DataFrame) -> pd.Series:
        """レース単位の表の行ごとに、◎が危ういか。"""
        return (races[HONMEI_TOP3] < self._line) | (races[HONMEI_DANGER] > 0).fillna(False)
