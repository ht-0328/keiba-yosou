"""区分ごとに学習する。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..dataset import DatasetBuilder, TrainingData, TrainingPeriod
from ..evaluation import TrainingReport
from ..feature import PredictionTiming
from ..ml_model import MEMBER_TYPES, Member
from ..repository import ModelRepository
from .model_segments import ModelSegments
from .training_workflow import TrainingWorkflow


class SegmentedTraining:
    """学習データを1回作り、区分（``ModelSegments``）ごとに ``TrainingWorkflow`` で学習して保存する。

    区分の行は、学習・検証・テストのどの期間でも同じ決まりで選ぶ（学習データの評価用の列で分ける）。
    分けない予想（区分が「全体」1つ）は、これまでの ``TrainingWorkflow`` と同じ置き場所に保存する。
    学習データに1行も無い区分（例: 14頭立て以上のレースが無い期間の4〜5番人気）は学習しない。
    """

    def __init__(self, segments: ModelSegments, dataset_builder: DatasetBuilder, period: TrainingPeriod,
                 root: Path, timings: Sequence[PredictionTiming], defaults_path: Path,
                 member_types: Sequence[type[Member]] = MEMBER_TYPES) -> None:
        self._segments = segments
        self._dataset_builder = dataset_builder
        self._period = period
        self._root = Path(root)
        self._timings = tuple(timings)
        self._defaults_path = defaults_path
        self._member_types = tuple(member_types)

    def read_training_data(self) -> TrainingData:
        """元DB から学習データを作る。この段だけが元DB を使う。"""
        return self._dataset_builder.build_training_data(self._period)

    def train(self, training_data: TrainingData, settings_path: Path | None) -> list[tuple[str, TrainingReport]]:
        """（区分の名前, 学習の結果）の並び。行の無い区分は入らない。"""
        present = [label for label in self._segments.labels()
                   if self._segments.rows(training_data.evaluation, label).any()]
        return [(label, self._train(label, training_data, settings_path)) for label in present]

    def _train(self, label: str, training_data: TrainingData, settings_path: Path | None) -> TrainingReport:
        rows = training_data.where(self._segments.rows(training_data.evaluation, label))
        repository = ModelRepository(self._segments.root_of(self._root, label), self._member_types)
        workflow = TrainingWorkflow(self._dataset_builder, self._period, repository, self._timings,
                                    self._defaults_path, self._member_types)
        return workflow.train(rows, settings_path)
