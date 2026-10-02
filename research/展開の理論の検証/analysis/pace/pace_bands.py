"""前半の速さ（z）を、ハイ・ミドル・スローに分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: ペースの区分の名前と、基準が無いレースの値。
SLOW, MIDDLE, HIGH, NO_BASELINE = "スロー", "ミドル", "ハイ", "基準なし"
#: 区分の並び（遅い順）。
PACE_ORDER: tuple[str, ...] = (SLOW, MIDDLE, HIGH)
#: ハイとスローを分ける z の線（展開予想の設計書 10 の 4. と同じ）。
Z_LINE = 0.5


class PaceBands:
    """z（速いほどプラス）を区分に直す。0.5 より大きければハイ、−0.5 より小さければスロー、そのあいだはミドル。

    z が欠損値（基準が作れない）なら「基準なし」。
    """

    def label(self, z: pd.Series) -> pd.Series:
        labels = np.select([z > Z_LINE, z < -Z_LINE, z.notna()], [HIGH, SLOW, MIDDLE], default=NO_BASELINE)
        return pd.Series(labels, index=z.index)
