"""1レースの1つの組の予想を、保存したモデルで予測する。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData
from yosou.shared.feature import PredictionTiming

from ..feature import GroupForecast, PriorForecasts
from .forecast_group import ForecastGroup
from .kind_forecaster import KindForecaster
from .kind_model_store import KindModelStore
from .kind_stacker import KindStacker


class GroupPredictor:
    """1つの組（前半・後半・着順）の、予測に使う予想を、その時点の保存したモデルで予測する（設計書 05 の図2）。

    予想ごとに、1頭ごと（か1レースごと）の予測用データに前の組の予測（V・S・T）の列を足し（``KindStacker``）、
    2つのモデルの予測を平均する（``KindForecaster``）。
    """

    def __init__(self, store: KindModelStore) -> None:
        self._store = store
        self._stacker = KindStacker()
        self._forecaster = KindForecaster()

    def predict(self, group: ForecastGroup, horses: PredictionData, races: PredictionData, priors: PriorForecasts,
                timing: PredictionTiming) -> GroupForecast:
        horse_parts = [horses.ids[[RACE_ID, HORSE_ID]]]
        race_parts = [races.ids[[RACE_ID]]]
        for kind in (kind for kind in group.kinds if kind.spec.for_prediction):
            base = races if kind.spec.per_race else horses
            data = self._stacker.apply(kind, base, priors)
            predicted = self._forecaster.predict(kind, self._store.load(kind, timing), data)
            (race_parts if kind.spec.per_race else horse_parts).append(predicted)
        return GroupForecast(pd.concat(horse_parts, axis=1), pd.concat(race_parts, axis=1))
