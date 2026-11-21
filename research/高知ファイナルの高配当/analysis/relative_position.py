"""相対位置: コーナーの順位を頭数でならした値（0 = 先頭、1 = 最後方）。頭数の違うレースの位置を比べるために使う。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RelativePosition:
    """順位の列と頭数の列 → 相対位置の列。順位が無い行は欠損値のまま。"""

    def of(self, rank: pd.Series, field_size: pd.Series) -> pd.Series:
        others = (field_size - 1).clip(lower=1)
        return (rank - 1) / others
