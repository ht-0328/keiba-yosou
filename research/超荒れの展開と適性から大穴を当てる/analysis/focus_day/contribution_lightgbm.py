"""LightGBM の学んだモデルで、特徴量ごとの寄与（出発点からの上げ下げのロジットを、列ごとに分けたもの）を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import LongshotData
from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.weighted_lightgbm import WeightedLightGbm


class ContributionLightGbm(WeightedLightGbm):
    """``WeightedLightGbm`` と同じに学び、``contributions`` で行 × 特徴量の寄与（ロジット）を返す（LightGBM の ``pred_contrib``）。
    寄与の行の合計 + 定数 = ``raw``。理由の文を作るのに使う。"""

    def contributions(self, data: LongshotData) -> pd.DataFrame:
        if self._encoder is None or self._model is None:
            raise RuntimeError("LightGBM のモデルがまだ学習していません")
        encoded = self._encoder.transform(data.features)
        values = np.asarray(self._model.predict(encoded, pred_contrib=True))
        return pd.DataFrame(values[:, :-1], columns=list(encoded.columns), index=data.features.index)
