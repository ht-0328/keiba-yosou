"""学んだモデル1つで、展開の型ごと（スロー・平均・ハイ）の確率を出し、予想のペースの確率で混ぜる。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from WIN5で人気薄の勝ち馬を狙う.analysis.longshot_forecast.longshot_data import LongshotData

from .scenario_materials import FORECAST, PACE
from .scenario_weights import ScenarioWeights


@dataclass(frozen=True)
class ScenarioPredictor:
    """``member`` は ``raw``（出発点からの上げ下げのロジット）を持つ学んだモデル。``weights`` は混ぜる重み。

    ``by_scenario`` は行 × 3（スロー・平均・ハイ）の確率、``mixed`` は混ぜた確率。展開の型を持たない作り（材料に
    展開の型の列が無い）では、3つとも同じ確率になる。"""

    member: object
    weights: ScenarioWeights

    def by_scenario(self, data: LongshotData) -> np.ndarray:
        if PACE not in data.features.columns:
            single = self._probability(data)
            return np.repeat(single[:, None], 3, axis=1)
        columns = []
        for code in (0.0, 1.0, 2.0):
            features = data.features.copy()
            features[PACE] = code
            columns.append(self._probability(LongshotData(data.ids, features, data.label, data.baseline, data.popularity,
                                                          data.market, data.categorical)))
        return np.stack(columns, axis=1)

    def mixed(self, data: LongshotData, scenario: np.ndarray) -> np.ndarray:
        return (scenario * self.weights.of(data.features[list(FORECAST)])).sum(axis=1)

    def _probability(self, data: LongshotData) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-(data.baseline.to_numpy() + self.member.raw(data))))
