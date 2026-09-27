"""学習に使っていない期間の学習データを、区分ごとの保存したモデルで予測する。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from ..dataset import TrainingData
from ..feature import PredictionTiming
from ..ml_model import MEMBER_TYPES, EnsembleModel, Member
from ..repository import ModelRepository
from .model_segments import ModelSegments


class SegmentedHoldoutPrediction:
    """学習データのうち、学習に使っていない期間（検証・テスト）の行を、区分ごとの保存したモデルで予測する
    （確率のずれを確かめるのに使う。穴馬の設計書 16 の 4）。

    ``SegmentedPrediction`` は予測用データ（1レース）を受け取り、区分を ID 列の横の列で分ける。こちらは学習データを受け取り、
    区分を評価用の列で分ける（学習のときの ``SegmentedTraining`` と同じ）。結果は、2つのモデルの確率の平均で、
    行の並びと index は ``data`` と同じ。
    """

    def __init__(self, segments: ModelSegments, root: Path,
                 member_types: Sequence[type[Member]] = MEMBER_TYPES) -> None:
        self._segments = segments
        self._root = Path(root)
        self._member_types = tuple(member_types)

    def predict(self, data: TrainingData, timing: PredictionTiming) -> pd.Series:
        """``data`` の行ごとの、その時点のモデルの確率（2つのモデルの平均）。"""
        timed = data.for_timing(timing)
        present = [label for label in self._segments.labels() if self._segments.rows(timed.evaluation, label).any()]
        parts = [self._one(timed, timing, label) for label in present]
        return pd.concat(parts).loc[timed.ids.index]

    def _one(self, data: TrainingData, timing: PredictionTiming, label: str) -> pd.Series:
        chosen = data.where(self._segments.rows(data.evaluation, label))
        repository = ModelRepository(self._segments.root_of(self._root, label), self._member_types)
        ensemble = EnsembleModel(repository.load(timing))
        return pd.Series(ensemble.predict_proba(chosen), index=chosen.ids.index)
