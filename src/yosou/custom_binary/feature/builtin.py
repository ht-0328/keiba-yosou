"""既存のまとまり単位の生成処理を、1項目ずつ選べる形に適合する。"""

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from yosou.shared.feature import EntryRecords, PredictionTiming
from yosou.shared.feature.feature_catalog import BASE_FEATURES, ODDS_FEATURES, POPULARITY_FEATURES
from yosou.shared.feature.feature_kind import FeatureKind
from yosou.shared.feature.group import (
    AptitudeFeatures, HorseFeatures, OddsFeatures, PedigreeFeatures, PeopleFeatures,
    PopularityHistoryFeatures, PreviousRunFeatures, RaceConditionFeatures, RecentFormFeatures,
    WorkoutFeatures,
)
from yosou.shared.feature.group.field_comparison_features import FieldComparisonFeatures


GROUPS = {
    "A": RaceConditionFeatures(), "B": HorseFeatures(), "C": PeopleFeatures(),
    "D": PreviousRunFeatures(), "E": RecentFormFeatures(), "F": AptitudeFeatures(),
    "G": FieldComparisonFeatures(), "H": PedigreeFeatures(), "I": WorkoutFeatures(),
    "J": PopularityHistoryFeatures(), "K": OddsFeatures(),
}
COMPARISON_DEPENDENCIES = ("斤量", "近5走の平均着差", "騎手の近1年の3着以内の割合")


@dataclass(frozen=True)
class GroupColumn:
    name: str
    description: str
    kind: FeatureKind
    known_from: PredictionTiming
    dependencies: tuple[str, ...]
    group: str

    def compute(self, records: EntryRecords, dependencies: Mapping[str, pd.Series]) -> pd.Series:
        return self.compute_cached(records, dependencies, {})

    def compute_cached(self, records: EntryRecords, dependencies: Mapping[str, pd.Series],
                       cache: dict[str, pd.DataFrame]) -> pd.Series:
        if self.group not in cache:
            generator = GROUPS[self.group]
            if self.group == "G":
                cache[self.group] = generator.build(records.entries, pd.DataFrame(dict(dependencies)))
            else:
                cache[self.group] = generator.build(records)
        return cache[self.group][self.name]


def builtin_features() -> tuple[GroupColumn, ...]:
    return tuple(GroupColumn(
        feature.name, feature.name, feature.kind, feature.known_from,
        COMPARISON_DEPENDENCIES if feature.group == "G" else (), feature.group,
    ) for feature in (*BASE_FEATURES, *POPULARITY_FEATURES, *ODDS_FEATURES))
