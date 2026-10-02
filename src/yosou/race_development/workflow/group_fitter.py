"""1つの組の予想を、決めた期間で学習し、予測する年を予測する。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.setting import HyperparameterSettings

from ..dataset import label_names as names
from ..feature import GroupForecast, PriorForecasts
from ..ml_model import OrderLambdaFitter, ValidationHalves
from ..tendency import TendencyFitter, TendencySink
from .development_model_kind import DevelopmentModelKind
from .forecast_group import ForecastGroup
from .kind_datasets import KindDatasets
from .kind_forecaster import KindForecaster
from .kind_trainer import KindTrainer
from .walk_forward_schedule import YearPeriod

#: ⑦ の予測の表に足す、2着・3着の割り当てのならしの指数 λ の列（その年のモデルで決めた値）。
ORDER_LAMBDA = "order_lambda"
#: 学習したモデルを受け取る関数（予想、学習した2つのモデル、⑦ なら λ・ほかは None）。学習（train）が保存に使う。
ModelSink = Callable[[DevelopmentModelKind, list[Any], float | None], None]


class GroupFitter:
    """1つの組の予想ごとに、LightGBM と CatBoost を学習し、予測する年のサンプルを予測する（設計書 05 の図5）。

    傾向の組は、既存の4つの予想を ``TendencyFitter`` で学習して予測する。
    年ごとの確かめのモデルは、予測を出したら捨てる（設計書 04 の「workflow/」）。学習（train）は ``sink``（傾向の組は
    ``tendency_sink``）を渡して、最新の年のモデルを受け取って保存する。⑦ は、検証データの後半で、2着・3着の割り当ての
    ならしの指数 λ も決めて、予測の表に入れる。
    """

    def __init__(self) -> None:
        self._trainer = KindTrainer()
        self._forecaster = KindForecaster()
        self._tendency = TendencyFitter()

    def fit_predict(self, group: ForecastGroup, period: YearPeriod, datasets: KindDatasets, priors: PriorForecasts,
                    timing: PredictionTiming, settings: HyperparameterSettings, sink: ModelSink | None = None,
                    tendency_sink: TendencySink | None = None, prediction_only: bool = False) -> GroupForecast:
        """予測する年（``period.predict_first_day`` から）の、組の全部の予想の予測。

        ``prediction_only`` を真にすると、予測に使う予想だけを学習する（比べるためだけの予想を飛ばす。学習（train）の着順の組）。
        その時点より後から学習する予想（``KindSpec.known_from``）も飛ばす。
        """
        if group is ForecastGroup.TENDENCY:
            return self._tendency.fit_predict(period, datasets.tendency, timing, settings, tendency_sink)
        horse_parts: list[pd.DataFrame] = []
        race_parts: list[pd.DataFrame] = []
        for kind in (kind for kind in group.kinds if self._fits(kind, timing, prediction_only)):
            predicted = self._fit_predict_kind(kind, period, datasets, priors, timing, settings, sink)
            (race_parts if kind.spec.per_race else horse_parts).append(predicted)
        return GroupForecast.joined(horse_parts, race_parts)

    def _fits(self, kind: DevelopmentModelKind, timing: PredictionTiming, prediction_only: bool) -> bool:
        """その予想を学習するか。"""
        return timing.is_at_or_after(kind.spec.known_from) and (kind.spec.for_prediction or not prediction_only)

    def _fit_predict_kind(self, kind: DevelopmentModelKind, period: YearPeriod, datasets: KindDatasets,
                          priors: PriorForecasts, timing: PredictionTiming, settings: HyperparameterSettings,
                          sink: ModelSink | None) -> pd.DataFrame:
        """1つの予想を学習して予測し、ID 列と予測の列の表にする。"""
        data = datasets.of(kind, priors)
        labeled = datasets.labeled(kind, data)
        train = labeled.between(period.train_first_day, period.valid_first_day).for_timing(timing)
        valid = labeled.between(period.valid_first_day, period.predict_first_day).for_timing(timing)
        members = self._trainer.fit(kind, train, valid, settings)
        target = data.between(period.predict_first_day, period.predict_end_day).for_timing(timing)
        keys = [RACE_ID] if kind.spec.per_race else [RACE_ID, HORSE_ID]
        predicted = pd.concat([target.ids[keys], self._forecaster.predict(kind, members, target)], axis=1)
        order_lambda = self._order_lambda(members, valid) if kind is DevelopmentModelKind.FINISH else None
        if sink is not None:
            sink(kind, members, order_lambda)
        if order_lambda is None:
            return predicted
        return predicted.assign(**{ORDER_LAMBDA: order_lambda})

    def _order_lambda(self, members: list[Any], valid: TrainingData) -> float:
        """検証データの後半で、⑦ の 2着・3着の割り当てのならしの指数 λ を決める（設計書 10 の 10.）。"""
        _, second_half = ValidationHalves().split(valid)
        win = EnsembleModel(members).predict_proba(second_half)
        finish = second_half.targets[names.FINISH].to_numpy()
        return OrderLambdaFitter().fit(win, second_half.ids[RACE_ID].to_numpy(), finish)
