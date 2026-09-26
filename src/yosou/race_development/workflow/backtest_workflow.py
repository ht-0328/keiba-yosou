"""年ごとの的中率と回収率の確かめの流れを進める。"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from pathlib import Path

import pandas as pd

from 共通 import db

from yosou.shared.dataset import RACE_DATE
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings

from ..betting import ReturnSummary
from ..evaluation import FinishYearMetrics, PlaceCalibration, StageYearMetrics
from ..feature import GroupForecast
from ..repository import BacktestArtifactRepository, DatasetRepository, OutOfSampleRepository
from ..setting import DEFAULT_SETTINGS_PATH
from .backtest_frames import BacktestFrames
from .backtest_report import BacktestReport
from .dataset_loader import TRAIN_FIRST_DAY, DatasetLoader
from .development_model_kind import DevelopmentModelKind
from .forecast_group import ForecastGroup
from .group_fitter import ORDER_LAMBDA
from .kind_datasets import KindDatasets
from .walk_forward_predictor import WalkForwardPredictor
from .walk_forward_schedule import WalkForwardSchedule
from .year_betting import YearBetting
from .year_market import YearMarket

#: 年ごとの確かめの時点（買うのは当日。設計書 15 の 18）。
TIMING = PredictionTiming.RACE_DAY


class BacktestWorkflow:
    """年ごとの確かめ（設計書 05 の図6・16 の 7）。ほかのクラスを順に呼んで、データを受け渡すだけで、自分では計算しない。

    学習データを作る → 前半・後半・着順の組の「学習に使っていない予測」を年ごとに作る → 年ごとに印と買い目を作って精算する →
    当たり具合と回収率の表にする。元DB を開くのは、学習データを作る段と、年ごとの確定オッズ・払戻を読む段だけ。
    途中の結果（学習データ・年ごとの予測・精算の表）は ``root`` の下に残し、止まったら続きから再開する。
    """

    def __init__(self, root: Path, db_path: Path | None, progress: Callable[[str], None] | None = None,
                 reuse_datasets: bool = False) -> None:
        self._root = Path(root)
        self._db_path = db_path
        self._progress = progress or (lambda message: None)
        self._artifacts = BacktestArtifactRepository(self._root / "backtest")
        self._datasets = DatasetLoader(DatasetRepository(self._root / "datasets"), db_path, self._progress, reuse_datasets)
        self._predictor = WalkForwardPredictor(OutOfSampleRepository(self._root / "out_of_sample"), self._progress)

    def run(self, years: Sequence[int], settings_path: Path | None) -> BacktestReport:
        settings = HyperparameterSettings.load(settings_path, defaults=DEFAULT_SETTINGS_PATH)
        years = sorted(years)
        datasets = self._datasets.load(years[-1])
        schedule = WalkForwardSchedule()
        early = self._forecast(ForecastGroup.EARLY, schedule, years, datasets, None, None, settings)
        late = self._forecast(ForecastGroup.LATE, schedule, years, datasets, early, None, settings)
        finish = self._forecast(ForecastGroup.FINISH, schedule, years, datasets, early, late, settings)
        frames = BacktestFrames(datasets)
        settled = pd.concat([self._settled(year, frames, early, finish) for year in years], ignore_index=True)
        stage_years = list(range(schedule.first_year(ForecastGroup.EARLY), years[-1] + 1))
        all_years = list(range(TRAIN_FIRST_DAY.year, years[-1] + 1))
        all_horses = frames.horses(all_years, early, late, finish)
        horses = all_horses[all_horses["年"].isin([str(year) for year in years])]
        return BacktestReport(
            returns=ReturnSummary().table(settled),
            finish=FinishYearMetrics().table(horses, self._finish_training_rows(years, datasets, early, late)),
            stages=StageYearMetrics().table(all_horses, frames.races(all_years, early, late), stage_years),
            calibration=PlaceCalibration().table(horses),
            order_lambdas=self._order_lambdas(finish, horses),
            years=tuple(years), settings=settings.to_dict(),
        )

    def save_text(self, name: str, text: str) -> Path:
        """結果の表（Markdown）を ``<root>/backtest/<name>.md`` に書く。"""
        return self._artifacts.save_text(name, text)

    def _forecast(self, group: ForecastGroup, schedule: WalkForwardSchedule, years: list[int], datasets: KindDatasets,
                  early: GroupForecast | None, late: GroupForecast | None,
                  settings: HyperparameterSettings) -> GroupForecast:
        """その組が予測を出せる最初の年から、確かめる最後の年までの予測。"""
        group_years = list(range(schedule.first_year(group), years[-1] + 1))
        return self._predictor.predict(group, group_years, datasets, early, late, TIMING, settings)

    def _settled(self, year: int, frames: BacktestFrames, early: GroupForecast, finish: GroupForecast) -> pd.DataFrame:
        """その年の精算した買い目。前に精算したものがあれば読む（予測が同じなら）。"""
        betting = frames.betting(year, early, finish)
        name = f"settled_{self._fingerprint(betting)}"
        if self._artifacts.exists(year, name):
            return self._artifacts.load(year, name)
        started = time.perf_counter()
        with db.open_db(self._db_path) as con:
            market = YearMarket.read(con, year)
        settled = YearBetting().settle(year, betting, market.odds, market.payouts, market.flags)
        self._artifacts.save(year, name, settled)
        self._progress(f"{year}年の買い目を精算した（{len(settled)}点、{(time.perf_counter() - started) / 60:.1f}分）")
        return settled

    def _fingerprint(self, table: pd.DataFrame) -> str:
        return f"{int(pd.util.hash_pandas_object(table, index=False).sum()) & 0xFFFFFFFF:08x}"

    def _finish_training_rows(self, years: list[int], datasets: KindDatasets, early: GroupForecast,
                              late: GroupForecast) -> dict[str, int]:
        """年 → その年の ⑦ のモデルの学習データの行数（早い年ほど少ないことを、表に並べて見せるため）。"""
        kind = DevelopmentModelKind.FINISH
        labeled = datasets.labeled(kind, datasets.of(kind, early, late))
        days = pd.to_datetime(labeled.ids[RACE_DATE])
        schedule = WalkForwardSchedule()
        return {
            str(year): int(((days >= pd.Timestamp(schedule.periods(ForecastGroup.FINISH, year).train_first_day))
                            & (days < pd.Timestamp(schedule.periods(ForecastGroup.FINISH, year).valid_first_day))).sum())
            for year in years
        }

    def _order_lambdas(self, finish: GroupForecast, horses: pd.DataFrame) -> dict[str, float]:
        """年 → ⑦ のならしの指数 λ。"""
        return {str(year): float(part[ORDER_LAMBDA].dropna().iloc[0]) for year, part in horses.groupby("年")
                if part[ORDER_LAMBDA].notna().any()}
