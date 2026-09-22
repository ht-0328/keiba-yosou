"""1頭ごとの特徴量をレース単位に集約して、特徴量の表を作る入口。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from .entry_records import EntryRecords
from .feature_builder import FeatureBuilder
from .feature_catalog import FeatureCatalog
from .prediction_timing import PredictionTiming
from .race_feature_group import RaceFeatureGroup
from .race_records import RaceRecords
from .value_types import typed_features


class RaceFeatureBuilder:
    """記録から、その時点で使うレース単位の特徴量の表（1行 = 1レース、列 = 特徴量）を作る（荒れ具合の設計書 05 の図3）。

    中で共通の ``FeatureBuilder`` を当日の時点で呼んで1頭ごとの特徴量を作り、まとまりごとのクラス（``groups``）で
    レース単位に集約して、1つの表にまとめる。時点で列を絞るのは、レース単位の一覧（``catalog``）だけで行う。
    1頭ごとの特徴量を先に絞ると、集約する元の列（1番人気の馬体重の増減 など）が無くなるためである。
    """

    def __init__(self, catalog: FeatureCatalog, horse_feature_builder: FeatureBuilder,
                 groups: Sequence[RaceFeatureGroup]) -> None:
        self._catalog = catalog
        self._horse_feature_builder = horse_feature_builder
        self._groups = tuple(groups)

    @property
    def catalog(self) -> FeatureCatalog:
        """作るレース単位の特徴量の一覧。"""
        return self._catalog

    def build(self, records: EntryRecords, payouts: pd.DataFrame, timing: PredictionTiming) -> pd.DataFrame:
        """``records.entries`` のレースごとの特徴量。index はレースID（出走の行に出てきた順）。

        ``payouts`` はレースごとの払戻（対象のレースと、その前の1年）。過去の荒れ率の材料になる。
        """
        horse_features = self._horse_feature_builder.build(records, PredictionTiming.RACE_DAY)
        race_records = RaceRecords(records, horse_features, payouts)
        parts = [group.build(race_records).reindex(race_records.race_ids) for group in self._groups]
        features = pd.concat(parts, axis=1)[list(self._catalog.names)]
        return typed_features(features, self._catalog.categorical)[list(self._catalog.columns_for(timing))]
