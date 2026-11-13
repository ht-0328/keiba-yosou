"""確かめの表に、レースごとの展開の型の混ぜる重み（予想のペースの確率。無ければ全体の割合）を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..scenario_forecast.scenario_materials import FORECAST, PACE
from ..scenario_forecast.scenario_weights import ScenarioWeights


@dataclass(frozen=True)
class RaceWeightsAttacher:
    """``materials`` は足す材料の表（race_id・horse_no・予想のペースの確率・展開の型）。予想の無いレースは、材料の表の全体の
    結果のペースの割合で混ぜる（区切りごとの学習の期間の割合とほぼ同じ）。足す列は w_0〜w_2。"""

    materials: pd.DataFrame

    def attach(self, frame: pd.DataFrame) -> pd.DataFrame:
        races = self.materials.drop_duplicates("race_id").set_index("race_id")
        prior = ScenarioWeights.prior_of(self.materials.drop_duplicates("race_id")[PACE])
        forecast = races.reindex(frame["race_id"].astype(str))[list(FORECAST)].reset_index(drop=True)
        weights = ScenarioWeights(np.asarray(prior)).of(forecast)
        return frame.reset_index(drop=True).assign(w_0=weights[:, 0], w_1=weights[:, 1], w_2=weights[:, 2])
