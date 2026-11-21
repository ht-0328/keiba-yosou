"""テスト用の偽物のモデル（馬番ごとに決めた確率を返す）。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from ..final_columns import HORSE_NO, MARKET_SHARE, TOP3, VALUE, WIN
from ..final_models import FinalModels


class FakeModels:
    """``win`` は 馬番 → 1着の確率、``top3`` は 馬番 → 3着以内の確率。決めていない馬は ``default_win``・``default_top3``。"""

    def __init__(self, win: Mapping[int, float], top3: Mapping[int, float], default_win: float = 0.05, default_top3: float = 0.2) -> None:
        self._win = dict(win)
        self._top3 = dict(top3)
        self._default = (default_win, default_top3)

    @staticmethod
    def scope(table: pd.DataFrame) -> pd.DataFrame:
        return FinalModels.scope(table)

    def score(self, table: pd.DataFrame) -> pd.DataFrame:
        scored = table.copy()
        numbers = scored[HORSE_NO].astype(int)
        scored[WIN] = numbers.map(lambda no: self._win.get(no, self._default[0]))
        scored[TOP3] = numbers.map(lambda no: self._top3.get(no, self._default[1]))
        scored[VALUE] = scored[WIN] / scored[MARKET_SHARE]
        return scored
