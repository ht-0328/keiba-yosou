"""記録から特徴量の表を作る入口。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .entry_records import EntryRecords
from .feature_catalog import FeatureCatalog
from .field_feature_group import FieldFeatureGroup
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
from .value_types import typed_features


class FeatureBuilder:
    """記録から、その時点で使う特徴量の表（1行 = 1頭、列 = 特徴量）を作る。

    まとまりごとのクラスを順に呼んで、1つの表にまとめるだけ。作り方は ``group/`` の各クラスにある。
    ``catalog`` は作る特徴量の一覧、``groups`` は G 以外のまとまりのクラス（省略すると A〜F・H・I の8つ）。
    ``field_groups`` は同じレースの馬どうしで比べるまとまりのクラス（省略すると G だけ。展開の予想は L・O を足す）。
    予想ごとにまとまりを足すときは、足した ``catalog`` と ``groups``（と ``field_groups``）を渡す。
    """

    def __init__(self, catalog: FeatureCatalog, groups: Sequence[FeatureGroup] | None = None,
                 field_groups: Sequence[FieldFeatureGroup] | None = None) -> None:
        self._catalog = catalog
        #: 自分の記録だけから作れるまとまり（G 以外）。
        self._groups: tuple[FeatureGroup, ...] = tuple(_base_groups() if groups is None else groups)
        #: G などは、ほかのまとまりの特徴量を、同じレースの馬どうしで比べて作る。
        self._field_groups: tuple[FieldFeatureGroup, ...] = (
            (FieldComparisonFeatures(),) if field_groups is None else tuple(field_groups)
        )

    @property
    def catalog(self) -> FeatureCatalog:
        """作る特徴量の一覧。"""
        return self._catalog

    def build(self, records: EntryRecords, timing: PredictionTiming) -> pd.DataFrame:
        """``records.entries`` の行ごとの特徴量。行の並びと index は ``records.entries`` と同じ。

        G（同じレースの馬との比較）は、``records.entries`` に入っている馬どうしで比べる。
        """
        own = pd.concat([group.build(records) for group in self._groups], axis=1)
        compared = [group.build(records.entries, own) for group in self._field_groups]
        features = pd.concat([own, *compared], axis=1)[list(self._catalog.names)]
        return typed_features(features, self._catalog.categorical)[list(self._catalog.columns_for(timing))]


def _base_groups() -> tuple[FeatureGroup, ...]:
    """まとまり A〜F・H・I（G 以外の、どの予想でも使うまとまり）。"""
    return (
        RaceConditionFeatures(), HorseFeatures(), PeopleFeatures(), PreviousRunFeatures(),
        RecentFormFeatures(), AptitudeFeatures(), PedigreeFeatures(), WorkoutFeatures(),
    )
