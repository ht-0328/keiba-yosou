"""学習データから、単位ごとの近さのモデルの一式を作る。"""

from __future__ import annotations

from yosou.shared.dataset import TrainingData

from ..dataset import GROUPS
from ..feature import CATALOG
from ..setting import BuyOrFadeSettings
from ..similarity import FeatureMatrix, SimilarityModelSet, UnitSimilarity
from ..unit import CourseUnitMap


class SimilarityTraining:
    """学習の流れ（設計書 05 の図1）。方針の時点の特徴量にする → 単位を決める → 単位ごとに3つのモデルを作る。"""

    def __init__(self, settings: BuyOrFadeSettings) -> None:
        self._settings = settings

    def train(self, data: TrainingData) -> SimilarityModelSet:
        """``data``（1番人気の学習データ）で学習した一式。"""
        timed = data.for_timing(self._settings.timing)
        unit_map = CourseUnitMap.from_rows(timed.features, self._settings.min_unit_rows)
        units = unit_map.units_of(timed.features)
        models = {unit: self._unit_model(timed.where(units == unit)) for unit in sorted(units.unique())}
        return SimilarityModelSet(unit_map, models, self._settings)

    def _unit_model(self, data: TrainingData) -> UnitSimilarity:
        matrix = FeatureMatrix(CATALOG, self._settings.excluded_features, self._settings.group_weights,
                               self._settings.add_missing_flags)
        return UnitSimilarity(matrix, self._settings.k).fit(data.features, data.targets[list(GROUPS)])
