"""学習の流れを進める。"""

from __future__ import annotations

from pathlib import Path

from ..dataset import DatasetBuilder, PeriodSplitter, SplitData
from ..evaluation import Evaluation, ModelEvaluator
from ..feature import PredictionTiming
from ..ml_model import MEMBER_TYPES, EnsembleModel, ProbabilityModel
from ..repository import ModelRepository
from ..setting import HyperparameterSettings
from .training_report import TrainingReport

#: 時点ごとの、学習したモデル（LightGBM と CatBoost）。
TrainedModels = dict[PredictionTiming, list[ProbabilityModel]]


class TrainingWorkflow:
    """学習の流れ（設計書 05 の図1）。

    設定を読む → 学習データを作る → 時期で分ける → 3つの時点ごとに2つのモデルを学習する → 保存する →
    検証データで当たり具合を確かめる。
    """

    def __init__(self, dataset_builder: DatasetBuilder, splitter: PeriodSplitter,
                 model_repository: ModelRepository) -> None:
        self._dataset_builder = dataset_builder
        self._splitter = splitter
        self._model_repository = model_repository
        self._evaluator = ModelEvaluator()

    def run(self, settings_path: Path | None) -> TrainingReport:
        """``settings_path`` の設定（None なら初期値）で学習する。モデルは合わせて6つ保存する。"""
        settings = HyperparameterSettings.load(settings_path)
        split = self._splitter.split(self._dataset_builder.build_training_data())
        trained = {timing: self._train(timing, split, settings) for timing in PredictionTiming}
        model_folders = {
            timing: self._model_repository.save(timing, models, settings)
            for timing, models in trained.items()
        }
        return TrainingReport(split, self._evaluate(trained, split), model_folders)

    def _train(self, timing: PredictionTiming, split: SplitData,
               settings: HyperparameterSettings) -> list[ProbabilityModel]:
        """1つの時点のモデルを学習する。学習データと検証データは、その時点で使う列だけにして渡す。"""
        train = split.train.for_timing(timing)
        valid = split.valid.for_timing(timing)
        return [model_type.from_settings(settings).fit(train, valid) for model_type in MEMBER_TYPES]

    def _evaluate(self, trained: TrainedModels, split: SplitData) -> list[Evaluation]:
        """検証データで当たり具合を測る。テストデータは最後に1回だけ確かめる用なので、ここでは使わない。"""
        evaluations: list[Evaluation] = []
        for timing, models in trained.items():
            evaluations += self._evaluator.evaluate(timing, EnsembleModel(models), split.valid)
        return evaluations
