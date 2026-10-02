"""④ 4コーナーの位置と ⑤ 上がりの速さの目的変数を付ける。"""

from __future__ import annotations

import pandas as pd

from ..feature.history import RelativeRank
from . import label_names as names


class LateLabeler:
    """④ 4コーナーの位置（0〜1）と ⑤ 上がりの速さ（0〜1）を付ける（設計書 06 の図6・10 の 7.・8.）。

    4コーナーの位置は ``(4コーナーの順位 − 1) ÷ (出走頭数 − 1)``、上がりの速さは
    ``(上がり3ハロンのレース内順位 − 1) ÷ (上がり3ハロンのある頭数 − 1)``。順位が無い馬は欠損値。
    """

    def __init__(self) -> None:
        self._relative_rank = RelativeRank()

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """列は ``4コーナーの位置``・``上がりの速さ``。行の並びと index は ``samples`` と同じ。"""
        return pd.DataFrame({
            names.CORNER4_POSITION: self._relative_rank.of(samples["corner4"], samples["field_size"]),
            names.CLOSING_SPEED: self._relative_rank.of(samples["last3f_rank"], samples["last3f_count"]),
        }, index=samples.index)
