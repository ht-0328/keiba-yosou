"""脚質の分け方を、何通りか並べる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..leaders import LEAD_RATE, POSITION_MEAN
from .style_variant import StyleVariant

#: 位置の区切り（0 が先頭、1 が最後方）。
_FRONT_LINE, _MIDDLE_LINE = 1 / 3, 2 / 3
#: 先頭率が高い（逃げたい）とみなす線。
_LEAD_LINE = 0.4

VARIANTS: tuple[StyleVariant, ...] = (
    StyleVariant("脚質（結果）", ("逃げ", "先行", "差し", "追込"), True),
    StyleVariant("最初のコーナーの位置（結果）", ("先頭", "前", "中", "後ろ"), True),
    StyleVariant("推定脚質（レース前）", ("逃げ", "先行", "差し", "追込"), False),
    StyleVariant("先頭率と位置（レース前）", ("先頭型", "前", "中", "後ろ"), False),
)


class StyleColumns:
    """``EarlyRunHistory`` を通した出走の表に、``VARIANTS`` の列を足す。

    - 脚質（結果）: JV-Data の脚質判定。
    - 最初のコーナーの位置（結果）: 先頭 = 最初のコーナーで1番手、前 = 前から3分の1まで、中 = 3分の2まで、後ろ = それより後ろ。
    - 推定脚質（レース前）: 直近3走の脚質の真ん中。
    - 先頭率と位置（レース前）: 近5走の先頭率が 0.4 以上なら先頭型、それ以外は近5走の序盤の位置の平均で 前・中・後ろ。
    分け方に当てはまらない馬（記録が無い・過去走が無い）は欠損値。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        rank = runners["first_corner_rank"].astype("Float64")
        position = ((rank - 1) / (runners["field_size"] - 1)).astype(float)
        after = np.select([rank.fillna(0) == 1, position <= _FRONT_LINE, position <= _MIDDLE_LINE, position > _MIDDLE_LINE],
                          ["先頭", "前", "中", "後ろ"], default=None)
        mean = runners[POSITION_MEAN]
        before = np.select([runners[LEAD_RATE] >= _LEAD_LINE, mean <= _FRONT_LINE, mean <= _MIDDLE_LINE, mean > _MIDDLE_LINE],
                           ["先頭型", "前", "中", "後ろ"], default=None)
        names = [variant.name for variant in VARIANTS]
        return runners.assign(**dict(zip(names, (runners["style"], after, runners["style_before"], before))))
