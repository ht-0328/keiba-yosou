"""記録から特徴量の表を作る入口。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .entry_records import EntryRecords
from .feature_catalog import FeatureCatalog
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

    まとまりごとのクラスを順に呼んで、1つの表にまとめるだけ。作り方は ``group/`` の各クラスにある。
    ``catalog`` は作る特徴量の一覧、``groups`` は G 以外のまとまりのクラス（省略すると A〜F・H・I の8つ）。
    予想ごとにまとまりを足すときは、足した ``catalog`` と ``groups`` を渡す。
    """

    def __init__(self, catalog: FeatureCatalog, groups: Sequence[FeatureGroup] | None = None) -> None:
        self._catalog = catalog
        #: 自分の記録だけから作れるまとまり（G 以外）。
        self._groups: tuple[FeatureGroup, ...] = tuple(_base_groups() if groups is None else groups)
        #: G は、ほかのまとまりの特徴量を、同じレースの馬どうしで比べて作る。
        self._field_comparison = FieldComparisonFeatures()

    @property
    def catalog(self) -> FeatureCatalog:
        """作る特徴量の一覧。"""
        return self._catalog

    def build(self, records: EntryRecords, timing: PredictionTiming) -> pd.DataFrame:
        """``records.entries`` の行ごとの特徴量。行の並びと index は ``records.entries`` と同じ。

        G（同じレースの馬との比較）は、``records.entries`` に入っている馬どうしで比べる。
        """
        own = pd.concat([group.build(records) for group in self._groups], axis=1)
        compared = self._field_comparison.build(records.entries, own)
        features = pd.concat([own, compared], axis=1)[list(self._catalog.names)]
        return self._typed(features)[list(self._catalog.columns_for(timing))]

    def _typed(self, features: pd.DataFrame) -> pd.DataFrame:
        """カテゴリ特徴量は文字列、数値特徴量は小数の列にそろえる。欠損値は欠損値のまま。"""
        categorical = self._catalog.categorical
        typed = {
            name: self._typed_column(features[name], name in categorical) for name in features.columns
        }
        return pd.DataFrame(typed, index=features.index)

    def _typed_column(self, values: pd.Series, is_categorical: bool) -> pd.Series:
        if is_categorical:
            return values.astype("str")
        return as_numbers(values)


def _base_groups() -> tuple[FeatureGroup, ...]:
    """まとまり A〜F・H・I（G 以外の、どの予想でも使うまとまり）。"""
    return (
        RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
        RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    )
