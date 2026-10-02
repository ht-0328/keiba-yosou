"""区分ごとのモデルで予測する。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from ..dataset import PredictionData
from ..ml_model import MEMBER_TYPES, EnsembleModel, Member
from ..repository import ModelRepository
from .model_segments import ModelSegments

#: 2つのモデルの確率の平均の列の名前（呼ぶ側が、予想の確率の列の名前に付け直す）。
AVERAGE = "平均"


class SegmentedPrediction:
    """予測用データの行を区分（``ModelSegments``）に分け、区分ごとに、その区分で学んだモデルで予測する。

    結果は、モデルごとの確率（LightGBM・CatBoost）と、その平均（``AVERAGE``）の列。行の並びと index は、予測用データの
    ID 列と同じ。予測用データに無い区分のモデルは読まない。
    """

    def __init__(self, segments: ModelSegments, root: Path,
                 member_types: Sequence[type[Member]] = MEMBER_TYPES) -> None:
        self._segments = segments
        self._root = Path(root)
        self._member_types = tuple(member_types)

    def predict(self, data: PredictionData) -> pd.DataFrame:
        present = [label for label in self._segments.labels() if self._segments.rows(data.ids, label).any()]
        parts = [self._one(data, label) for label in present]
        return pd.concat(parts).loc[data.ids.index]

    def _one(self, data: PredictionData, label: str) -> pd.DataFrame:
        chosen = data.where(self._segments.rows(data.ids, label))
        repository = ModelRepository(self._segments.root_of(self._root, label), self._member_types)
        ensemble = EnsembleModel(repository.load(data.timing))
        members = ensemble.predict_members(chosen)
        return pd.DataFrame({**members, AVERAGE: ensemble.combine(members)}, index=chosen.ids.index)
