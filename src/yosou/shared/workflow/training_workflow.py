"""学習の流れを進める。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ..dataset import DatasetBuilder, PeriodSplitter, SplitData, TrainingData, TrainingPeriod
from ..evaluation import Evaluation, ModelEvaluator, TrainingReport
from ..feature import PredictionTiming
from ..ml_model import MEMBER_TYPES, EnsembleModel, ProbabilityModel
from ..repository import ModelRepository
from ..setting import HyperparameterSettings

#: 時点ごとの、学習したモデル（LightGBM と CatBoost）。
TrainedModels = dict[PredictionTiming, list[ProbabilityModel]]


class TrainingWorkflow:
    """学習の流れ（設計書 05 の図1）。どの予想でも同じなので、``shared`` に置く。

    設定を読む → 学習データを作る → 時期で分ける → 時点ごとに2つのモデルを学習する → 保存する →
    検証データで当たり具合を確かめる。予想ごとに違うのは、渡される ``dataset_builder`` の中身と、
    学習する時点（``timings``）の数だけである。

    元DB が要るのは学習データを作る段（``read_training_data()``）だけなので、コマンドは、その段を
    終えたら DB を閉じてロックを手放してから ``train()`` を呼ぶ。学習は何分もかかり、そのあいだ
    ほかの道具が DB を開けなくなるためである。
    """

    def __init__(self, dataset_builder: DatasetBuilder, period: TrainingPeriod,
                 model_repository: ModelRepository, timings: Sequence[PredictionTiming],
                 defaults_path: Path) -> None:
        """``timings`` は学習する時点、``defaults_path`` はその予想のハイパーパラメータの初期値のファイル。"""
        self._dataset_builder = dataset_builder
        self._period = period
        self._splitter = PeriodSplitter(period)
        self._model_repository = model_repository
        self._timings = tuple(timings)
        self._defaults_path = defaults_path
        self._evaluator = ModelEvaluator()

    def run(self, settings_path: Path | None) -> TrainingReport:
        """学習データを作って、そのまま学習する（``read_training_data()`` → ``train()``）。"""
        return self.train(self.read_training_data(), settings_path)

    def read_training_data(self) -> TrainingData:
        """元DB から学習データを作る。この段だけが元DB を使う。"""
        return self._dataset_builder.build_training_data(self._period)

    def train(self, training_data: TrainingData, settings_path: Path | None) -> TrainingReport:
        """``settings_path`` の設定（None なら初期値）で学習する。モデルは 時点の数 × 2つ保存する。元DB は使わない。"""
        settings = HyperparameterSettings.load(settings_path, defaults=self._defaults_path)
        split = self._splitter.split(training_data)
        trained = {timing: self._train(timing, split, settings) for timing in self._timings}
        model_folders = {
            timing: self._model_repository.save(timing, models, settings)
            for timing, models in trained.items()
        }
        return TrainingReport(self._period, split, self._evaluate(trained, split), model_folders)

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
