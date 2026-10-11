"""馬体重の表 W の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import names


@dataclass(frozen=True)
class WeightTable:
    """表 W。``frame`` は帯3つ（``BANDS``）ごとの 件数・差・増減の帯の差・縮めた差、``as_of`` は使ったレースの最後の開催日（無ければ None）。"""

    frame: pd.DataFrame
    as_of: date | None

    def lookup(self, bands: pd.DataFrame) -> pd.Series:
        """``bands``（``BANDS`` の列）の行ごとの縮めた差 W（index は ``bands`` と同じ）。帯の無い行や表に無いマスは欠損値。"""
        keys = bands[list(names.BANDS)]
        found = keys.merge(self.frame[[*names.BANDS, names.GAP]], on=list(names.BANDS), how="left")[names.GAP]
        return pd.Series(found.to_numpy(dtype="float64"), index=bands.index)
