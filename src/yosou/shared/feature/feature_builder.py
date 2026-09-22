"""記録から特徴量の表を作る入口。"""

from __future__ import annotations

import pandas as pd

from .entry_records import EntryRecords
from .feature_catalog import CATEGORICAL_FEATURES, FEATURE_NAMES
from .feature_group import FeatureGroup
from .group import (
    AptitudeFeatures,
    FieldComparisonFeatures,
    HorseFeatures,
    PedigreeFeatures,
    PeopleFeatures,
    PreviousRunFeatures,
    RaceConditionFeatures,
    RecentFormFeatures,
    WorkoutFeatures,
)
from .prediction_timing import PredictionTiming
from .value_types import as_numbers


class FeatureBuilder:
    """記録から、その時点で使う特徴量の表（1行 = 1頭、列 = 特徴量）を作る。

    まとまり（A〜I）ごとのクラスを順に呼んで、1つの表にまとめるだけ。作り方は ``group/`` の各クラスにある。
    """

    def __init__(self) -> None:
        #: 自分の記録だけから作れるまとまり（G 以外）。
        self._groups: tuple[FeatureGroup, ...] = (
            RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
            RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
        )
        #: G は、ほかのまとまりの特徴量を、同じレースの馬どうしで比べて作る。
        self._field_comparison = FieldComparisonFeatures()

    def build(self, records: EntryRecords, timing: PredictionTiming) -> pd.DataFrame:
        """``records.entries`` の行ごとの特徴量。行の並びと index は ``records.entries`` と同じ。

        G（同じレースの馬との比較）は、``records.entries`` に入っている馬どうしで比べる。
        """
        own = pd.concat([group.build(records) for group in self._groups], axis=1)
        compared = self._field_comparison.build(records.entries, own)
        features = pd.concat([own, compared], axis=1)[list(FEATURE_NAMES)]
        return self._typed(features)[list(timing.feature_columns())]

    def _typed(self, features: pd.DataFrame) -> pd.DataFrame:
        """カテゴリ特徴量は文字列、数値特徴量は小数の列にそろえる。欠損値は欠損値のまま。"""
        typed = {name: self._typed_column(features[name]) for name in features.columns}
        return pd.DataFrame(typed, index=features.index)

    def _typed_column(self, values: pd.Series) -> pd.Series:
        if values.name in CATEGORICAL_FEATURES:
            return values.astype("str")
        return as_numbers(values)
