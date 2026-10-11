"""出走ごとの増減・間隔・馬齢から、表 W を引いて体重の割引の列を作る。"""

from __future__ import annotations

import pandas as pd

from . import names
from .weight_bands import WeightBands
from .weight_table import WeightTable

#: 予測用データ・学習データの特徴量にある元の列（馬の力の材料 M の名前。当日の表にある）。
WEIGHT_CHANGE, INTERVAL_DAYS, AGE = "weight_change", "interval_days", "age"


class WeightDiscountColumns:
    """特徴量の表（増減・前走からの日数・馬齢の列を持つ）の行ごとに、帯に分けて表 W を引く。

    値は3着以内の確率のポイント（負なら、市場の見立てより来ない）。帯の無い馬（初出走・馬体重の未発表）は欠損値。
    例（架空）: 3歳・中2週・−12kg のマスが −0.03 なら、体重の割引は −0.03。
    """

    def __init__(self, table: WeightTable) -> None:
        self._table = table
        self._bands = WeightBands()

    def of(self, features: pd.DataFrame) -> pd.DataFrame:
        """列は ``DISCOUNT`` の1つ。行の並びと index は ``features`` と同じ。"""
        bands = self._bands.of(features[WEIGHT_CHANGE], features[INTERVAL_DAYS], features[AGE])
        return pd.DataFrame({names.DISCOUNT: self._table.lookup(bands)}, index=features.index).astype("float64")
