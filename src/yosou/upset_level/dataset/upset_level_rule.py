"""券種ごとの荒れ具合の線引き。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .bet_type import BetType
from .upset_level import UpsetLevel

#: 券種ごとの線引き（中荒れ・大荒れ・超荒れの最初の額。100円あたりの円）。設計書 10 の表の写しで、線引きの唯一の置き場所。
THRESHOLDS: dict[BetType, tuple[int, int, int]] = {
    BetType.WIN: (500, 1_000, 3_000),
    BetType.QUINELLA: (1_000, 3_000, 10_000),
    BetType.TRIO: (3_000, 10_000, 50_000),
    BetType.TRIFECTA: (20_000, 100_000, 500_000),
}


class UpsetLevelRule:
    """払戻から荒れ具合（固い 0・中荒れ 1・大荒れ 2・超荒れ 3）を決める（設計書 10）。

    目的変数（``UpsetLevelLabeler``）と、過去の荒れ率（まとまり E）の両方がこの1つを使うので、線引きを変えても
    2つが食い違わない。
    """

    def __init__(self, thresholds: dict[BetType, tuple[int, int, int]] | None = None) -> None:
        self._thresholds = dict(THRESHOLDS if thresholds is None else thresholds)

    def thresholds_of(self, bet: BetType) -> tuple[int, int, int]:
        """その券種の、中荒れ・大荒れ・超荒れの最初の額。"""
        return self._thresholds[bet]

    def level_of(self, bet: BetType, yen: float | None) -> UpsetLevel | None:
        """1つの払戻の荒れ具合。払戻が無ければ None。"""
        if yen is None or np.isnan(yen):
            return None
        return UpsetLevel(int(self.levels_of(bet, pd.Series([float(yen)])).iloc[0]))

    def levels_of(self, bet: BetType, yen: pd.Series) -> pd.Series:
        """払戻の列から、荒れ具合のクラス番号の列（小数。払戻が無ければ欠損値）。"""
        bins = [-np.inf, *self._thresholds[bet], np.inf]
        levels = pd.cut(yen.astype("float64"), bins=bins, labels=UpsetLevel.class_labels(), right=False)
        return pd.to_numeric(levels, errors="coerce").astype("float64")

    def is_upset_or_more(self, bet: BetType, yen: pd.Series) -> pd.Series:
        """払戻の列から、中荒れ以上か（払戻が無ければ False）。"""
        first_upset, _, _ = self._thresholds[bet]
        return yen.astype("float64").ge(first_upset).fillna(False)
