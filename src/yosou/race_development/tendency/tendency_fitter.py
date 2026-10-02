"""既存の予想を、決めた期間で学習し、予測する年を予測する（傾向の組）。"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings

from ..feature import GroupForecast
from .tendency_datasets import TendencyDatasets
from .tendency_source import TendencySource
from .tendency_unit import TendencyUnit
from .unit_table_combiner import UnitTableCombiner

if TYPE_CHECKING:  # 型の注釈にだけ使う（実行時に読み込むと、workflow との参照が循環する）
    from ..workflow.walk_forward_schedule import YearPeriod

#: 学習したモデルを受け取る関数（既存の予想、単位、学習した2つのモデル）。学習（train）が保存に使う。
TendencySink = Callable[[TendencySource, TendencyUnit, list[Any]], None]


class TendencyFitter:
    """既存の4つの予想を、単位（区分・券種）ごとに LightGBM と CatBoost で学習し、予測する年のサンプルを予測する。

    期間の区切りは、展開の予想の組と同じ ``YearPeriod``（学習・検証・予測）。学習データに行の無い単位
    （例: 14頭立て以上のレースが無い期間の 4〜5番人気）は学習しない。その時点で既存の予想がモデルを持たなければ、何も出さない。
    """

    def __init__(self) -> None:
        self._combiner = UnitTableCombiner()

    def fit_predict(self, period: YearPeriod, datasets: TendencyDatasets, timing: PredictionTiming,
                    settings: HyperparameterSettings, sink: TendencySink | None = None) -> GroupForecast:
        """予測する年（``period.predict_first_day`` から）の、傾向の組の予測。"""
        horse_parts: list[pd.DataFrame] = []
        race_parts: list[pd.DataFrame] = []
        for source in (source for source in TendencySource if source.predicts_at(timing)):
            table = self._source(source, period, datasets, timing, settings, sink)
            (race_parts if source.spec.per_race else horse_parts).append(table)
        return GroupForecast.joined(horse_parts, race_parts)

    def _source(self, source: TendencySource, period: YearPeriod, datasets: TendencyDatasets, timing: PredictionTiming,
                settings: HyperparameterSettings, sink: TendencySink | None) -> pd.DataFrame:
        """1つの既存の予想の、単位ごとの予測を1つにまとめた表。"""
        data = datasets.of(source)
        keys = [RACE_ID] if source.spec.per_race else [RACE_ID, HORSE_ID]
        parts = [self._unit(source, unit, data, period, timing, settings, sink, keys) for unit in source.spec.units]
        return self._combiner.combine(parts, keys)

    def _unit(self, source: TendencySource, unit: TendencyUnit, data: TrainingData, period: YearPeriod, timing: PredictionTiming,
              settings: HyperparameterSettings, sink: TendencySink | None, keys: list[str]) -> pd.DataFrame | None:
        """1つの単位を学習して予測し、ID 列と予測の列の表にする。学習か検証の行が無ければ None。"""
        labeled = unit.samples(data)
        train = labeled.between(period.train_first_day, period.valid_first_day).for_timing(timing)
        valid = labeled.between(period.valid_first_day, period.predict_first_day).for_timing(timing)
        if len(train) == 0 or len(valid) == 0:
            return None
        members = unit.fit(train, valid, settings)
        if sink is not None:
            sink(source, unit, members)
        target = unit.targets(data).between(period.predict_first_day, period.predict_end_day).for_timing(timing)
        if len(target) == 0:
            return None
        return pd.concat([target.ids[keys], unit.predict(members, target)], axis=1)
