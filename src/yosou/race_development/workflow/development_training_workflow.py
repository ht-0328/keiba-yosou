"""学習（予測に使うモデルを作って保存する）の流れを進める。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings

from ..feature import GroupForecast, PriorForecasts
from ..repository import DatasetRepository, OutOfSampleRepository
from ..setting import DEFAULT_SETTINGS_PATH
from ..tendency import TendencyModelStore, TendencySink, TendencySource, TendencyUnit
from .dataset_loader import DatasetLoader
from .development_model_kind import DevelopmentModelKind
from .forecast_group import ForecastGroup
from .group_fitter import GroupFitter, ModelSink
from .kind_datasets import KindDatasets
from .kind_model_store import KindModelStore
from .walk_forward_predictor import WalkForwardPredictor
from .walk_forward_schedule import WalkForwardSchedule


@dataclass(frozen=True)
class SavedModel:
    """保存した1つの予想・時点のモデル。"""

    kind: DevelopmentModelKind
    timing: PredictionTiming
    folder: Path
    tree_counts: tuple[int, ...]
    order_lambda: float | None


class DevelopmentTrainingWorkflow:
    """予測に使うモデルを、時点ごとに学習して保存する（設計書 05 の図1）。ほかのクラスを順に呼ぶだけで、自分では計算しない。

    予測に使うのは、``year`` 年のモデル（学習は組の最初の年 〜（year−1）年9月、検証は（year−1）年10〜12月）で、
    年ごとの確かめの ``year`` 年のモデルと同じ作り方である。傾向の組（既存の4つの予想）のモデルも、同じ作り方で学習して保存する。
    前半・後半・着順のモデルの学習データに入れる前の組の予測（V・S・T）は、年ごとに学習し直して作った
    「学習に使っていない予測」（``WalkForwardPredictor``。年ごとの確かめと共有）。
    """

    def __init__(self, root: Path, db_path: Path | None, progress: Callable[[str], None] | None = None) -> None:
        self._root = Path(root)
        self._progress = progress or (lambda message: None)
        self._loader = DatasetLoader(DatasetRepository(self._root / "datasets"), db_path, self._progress)
        self._predictor = WalkForwardPredictor(OutOfSampleRepository(self._root / "out_of_sample"), self._progress)
        self._store = KindModelStore(self._root / "models")
        self._tendency_store = TendencyModelStore(self._root / "models")
        self._schedule = WalkForwardSchedule()
        self._fitter = GroupFitter()

    def run(self, year: int, timings: Sequence[PredictionTiming], settings_path: Path | None) -> list[SavedModel]:
        settings = HyperparameterSettings.load(settings_path, defaults=DEFAULT_SETTINGS_PATH)
        datasets = self._loader.load(year)
        saved: list[SavedModel] = []
        for timing in timings:
            saved += self._train_timing(year, timing, datasets, settings)
        return saved

    def _train_timing(self, year: int, timing: PredictionTiming, datasets: KindDatasets,
                      settings: HyperparameterSettings) -> list[SavedModel]:
        """1つの時点の、4つの組のモデルを学習して保存する。"""
        saved: list[SavedModel] = []
        sink, tendency_sink = self._sink(timing, settings, saved), self._tendency_sink(timing, settings)
        tendency = self._group(ForecastGroup.TENDENCY, year, datasets, PriorForecasts(), timing, settings, sink, tendency_sink)
        priors = PriorForecasts(tendency)
        priors = priors.with_early(self._group(ForecastGroup.EARLY, year, datasets, priors, timing, settings, sink))
        priors = priors.with_late(self._group(ForecastGroup.LATE, year, datasets, priors, timing, settings, sink))
        finish = ForecastGroup.FINISH  # 着順の組は後の組が無いので、前の年の予測は作らない
        self._fitter.fit_predict(finish, self._schedule.periods(finish, year), datasets, priors, timing, settings, sink)
        self._progress(f"{timing.label}のモデルを保存した（{len(saved)}つの予想と、既存の予想）")
        return saved

    def _group(self, group: ForecastGroup, year: int, datasets: KindDatasets, priors: PriorForecasts,
               timing: PredictionTiming, settings: HyperparameterSettings, sink: ModelSink,
               tendency_sink: TendencySink | None = None) -> GroupForecast:
        """前の年までの「学習に使っていない予測」と、``year`` 年のモデル（保存する）の予測をつないだもの。"""
        previous_years = list(range(self._schedule.first_year(group), year))
        before = self._predictor.predict(group, previous_years, datasets, priors, timing, settings)
        latest = self._fitter.fit_predict(group, self._schedule.periods(group, year), datasets, priors, timing,
                                          settings, sink, tendency_sink)
        return GroupForecast.concat([before, latest])

    def _sink(self, timing: PredictionTiming, settings: HyperparameterSettings,
              saved: list[SavedModel]) -> Callable[[DevelopmentModelKind, list[Any], float | None], None]:
        """学習したモデルを保存し、``saved`` に書き足す関数。比べる基準（前半・後半を入れない着順のモデル）は保存しない。"""
        def save(kind: DevelopmentModelKind, members: list[Any], order_lambda: float | None) -> None:
            if kind is DevelopmentModelKind.FINISH_PLAIN:
                return
            folder = self._store.save(kind, timing, members, settings, order_lambda)
            saved.append(SavedModel(kind, timing, folder, tuple(member.tree_count for member in members), order_lambda))
        return save

    def _tendency_sink(self, timing: PredictionTiming, settings: HyperparameterSettings) -> TendencySink:
        """既存の予想の学習したモデルを保存する関数。"""
        def save(source: TendencySource, unit: TendencyUnit, members: list[Any]) -> None:
            self._tendency_store.save(source, unit, timing, members, settings)
        return save
