"""組の形: 組の馬の人気の帯（人気馬・中穴・大穴）を 人・中・大 の順に並べた文字（例 ``人中``・``人中大``）を、券種の組の表に付ける。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from .popularity_band import FAVORITE, LONGSHOT, MIDDLE, PopularityBand

#: 組の表に付ける列。
FORM = "form"
_ORDER = {FAVORITE: 0, MIDDLE: 1, LONGSHOT: 2}


class ComboForms:
    """``horses`` は ``horse_no``・``popularity``（単勝オッズの順）を持つ馬の表。``attach(table, keys)`` は ``keys`` の列（馬番）から形を付けて返す。
    枠連（枠番の組）には付けない。"""

    def __init__(self, horses: pd.DataFrame, band: PopularityBand | None = None) -> None:
        bands = (band or PopularityBand()).band_of(pd.to_numeric(horses["popularity"], errors="coerce"))
        self._band_of = dict(zip(horses["horse_no"].astype(int), bands.fillna(LONGSHOT).astype(str), strict=True))

    def attach(self, table: pd.DataFrame, keys: Sequence[str]) -> pd.DataFrame:
        letters = np.vstack([table[key].astype(int).map(self._band_of).fillna(LONGSHOT).to_numpy() for key in keys]).T if len(table) else np.empty((0, len(keys)))
        return table.assign(**{FORM: ["".join(sorted(row, key=_ORDER.get)) for row in letters]})
