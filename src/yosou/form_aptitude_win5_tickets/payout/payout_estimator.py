"""配当の見積もりの式。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .payout_features import FEATURE_COLUMNS


@dataclass(frozen=True)
class PayoutEstimator:
    """過去の WIN5 の当たり組の 100円あたりの払戻の対数を、組の材料（``PayoutFeatures``）の1次式で当てる式（設計書 10 の 2.）。

    ``log(払戻) = 切片 + 傾き1 × 市場の組の確率の逆数の対数 + 傾き2 × キャリーオーバーの比の対数 + 外れ``。
    戻すときは ``exp(式の値)`` に、式を作った当たり組の ``exp(外れ)`` の平均（``smear``）を掛けて「平均の配当」にする。
    ``residual_std`` は外れの散らばり（標準偏差）、``count`` は式を作るのに使った当たり組の数。
    """

    slopes: tuple[float, float]
    intercept: float
    smear: float
    residual_std: float
    count: int

    @classmethod
    def fit(cls, features: pd.DataFrame, payouts: pd.Series) -> PayoutEstimator:
        """当たり組の材料と払戻（100円あたり。0 より大きいこと）から、傾き・切片・戻すときの補正を決める。"""
        if len(features) < len(FEATURE_COLUMNS) + 1:
            raise ValueError(f"配当の見積もりの式を作るには、当たり組が {len(FEATURE_COLUMNS) + 1} つ以上要ります（{len(features)} つ）")
        x = features[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
        y = np.log(np.asarray(payouts, dtype=float))
        model = LinearRegression().fit(x, y)
        residual = y - model.predict(x)
        slope_inverse, slope_carry = (float(value) for value in model.coef_)
        return cls((slope_inverse, slope_carry), float(model.intercept_), float(np.mean(np.exp(residual))),
                   float(np.std(residual)), len(y))

    def estimate(self, features: pd.DataFrame) -> np.ndarray:
        """組ごとの式の値（100円あたりの配当の平均の見込み。上限と自分の1票はまだ当てていない）。"""
        x = features[list(FEATURE_COLUMNS)].to_numpy(dtype=float)
        return np.exp(self.intercept + x @ np.asarray(self.slopes)) * self.smear

    def to_dict(self) -> dict[str, Any]:
        return {
            "傾き": dict(zip(FEATURE_COLUMNS, self.slopes, strict=True)), "切片": self.intercept,
            "戻すときの補正": self.smear, "外れの散らばり": self.residual_std, "使った当たり組の数": self.count,
        }

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> PayoutEstimator:
        slopes = values["傾き"]
        return cls((float(slopes[FEATURE_COLUMNS[0]]), float(slopes[FEATURE_COLUMNS[1]])), float(values["切片"]),
                   float(values["戻すときの補正"]), float(values["外れの散らばり"]), int(values["使った当たり組の数"]))
