"""展開の型（スロー・平均・ハイ）を混ぜる重み。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ScenarioWeights:
    """予想のペースの確率（行 × 3。スロー・平均・ハイの順）を、行ごとに合計 1 にそろえる。予想の無い行は ``prior``
    （学習の期間の、結果のペースの割合）を使う。"""

    prior: np.ndarray

    def of(self, forecast: pd.DataFrame) -> np.ndarray:
        values = forecast.to_numpy(dtype=float)
        missing = np.isnan(values).any(axis=1)
        values = np.where(missing[:, None], self.prior[None, :], values)
        return values / values.sum(axis=1, keepdims=True)

    @staticmethod
    def prior_of(pace_codes: pd.Series) -> np.ndarray:
        """結果のペースの列（0・1・2・欠損値）から、3つの割合。結果の分からない行は数えない。"""
        counts = pace_codes.dropna().astype(int).value_counts().reindex([0, 1, 2], fill_value=0).to_numpy(dtype=float)
        return counts / counts.sum() if counts.sum() else np.full(3, 1 / 3)
