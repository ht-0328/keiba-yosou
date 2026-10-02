"""単位ごとの近さのモデルの一式。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from ..feature import CATALOG
from ..setting import BuyOrFadeSettings
from ..unit import CourseUnitMap
from .score_columns import SCORE_COLUMNS, UNIT
from .unit_similarity import UnitSimilarity


@dataclass(frozen=True)
class SimilarityModelSet:
    """学習した近さのモデルの一式。単位の決め方、単位の名前 → 3つのモデル、学習に使った方針。"""

    unit_map: CourseUnitMap
    units: Mapping[str, UnitSimilarity]
    settings: BuyOrFadeSettings

    def scores(self, features: pd.DataFrame) -> pd.DataFrame:
        """行ごとの単位と、3つのグループへの近さの点数。学習した方針の時点の列だけを使う。"""
        timed = features[list(self._timed_columns(features))]
        units = self.unit_map.units_of(timed)
        parts = [self.units[unit].scores(timed[units == unit]) for unit in units.unique()]
        if not parts:
            return pd.DataFrame(columns=[UNIT, *SCORE_COLUMNS.values()])
        return pd.concat([units.rename(UNIT), pd.concat(parts).reindex(timed.index)], axis=1)

    def _timed_columns(self, features: pd.DataFrame) -> list[str]:
        """学習した時点で分かる特徴量の列（``features`` にあるもの）。"""
        known = set(CATALOG.columns_for(self.settings.timing))
        return [column for column in features.columns if column in known]
