"""予測の結果に、危険度と危険かを足す。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

#: 足す列の名前（予測の結果の表にも、そのまま出す）。
BASE_OUT = "オッズから見た4着以下の確率"
DANGER = "危険度"
IS_DANGER = "危険"


class DangerJudge:
    """予測の結果に、オッズから見た4着以下の確率（基準）・危険度（予想 − 基準）・危険か（危険度が人気帯の線以上）を足す。

    ``thresholds`` は人気帯の名前 → 危険度の線（学習のときに検証期間で決めたもの）。線の無い人気帯は、危険と判定しない。
    例: 1番人気の線が 0.06 で、予想 0.42・基準 0.33 の1番人気は、危険度 0.09 で「危険」。
    """

    def __init__(self, thresholds: Mapping[str, float]) -> None:
        self._thresholds = dict(thresholds)

    def judge(self, probability: pd.Series, base: pd.Series, band: pd.Series) -> pd.DataFrame:
        danger = probability - base
        line = band.map(self._thresholds).astype(float)
        return pd.DataFrame({
            BASE_OUT: base, DANGER: danger, IS_DANGER: np.where(danger >= line.fillna(np.inf), "危険", ""),
        }, index=probability.index)
