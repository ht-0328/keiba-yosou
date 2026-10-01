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

from ..betting import MODEL_MARK_RULE, POPULARITY_MARK_RULE, ReturnSummary, ValueLineChoice
from ..betting import column_names as bet
from ..betting.value_line_choice import MODEL_VALUE_RULE
from ..evaluation import FinishYearMetrics, PlaceCalibration, StageYearMetrics, UnlabeledRaceTable
from ..feature import ODDS_WIN_PROBABILITY, WIN_PROBABILITY, GroupForecast, PriorForecasts
from ..repository import BacktestArtifactRepository, DatasetRepository, OutOfSampleRepository
from ..setting import DEFAULT_SETTINGS_PATH
from .backtest_frames import BacktestFrames
from .backtest_report import BacktestReport
from .dataset_loader import DB_LOCK_WAIT_SECONDS, TRAIN_FIRST_DAY, DatasetLoader
from .development_model_kind import DevelopmentModelKind
from .forecast_group import ForecastGroup
from .group_fitter import ORDER_LAMBDA
from .kind_datasets import KindDatasets
from .walk_forward_predictor import WalkForwardPredictor
from .walk_forward_schedule import WalkForwardSchedule
from .year_betting import YearBetting
from .year_market import YearMarket

#: 年ごとの確かめの時点の既定（買うのは当日。設計書 15 の 18）。``backtest --timing`` で前日・木曜にもできる。
DEFAULT_TIMING = PredictionTiming.RACE_DAY
#: 買い方の名前の後ろ（モデルの ⑦ と、オッズを足した ⑦）。オッズを足した ⑦ の買い目は、名前の後ろを置き換えて区別する。
MODEL_LABEL, ODDS_LABEL = "モデル", "オッズ入り"


class BacktestWorkflow:
    """年ごとの確かめ（設計書 05 の図6・16 の 7）。ほかのクラスを順に呼んで、データを受け渡すだけで、自分では計算しない。

    学習データを作る → 傾向・前半・後半・着順の組の「学習に使っていない予測」を年ごとに作る → 年ごとに印と買い目を作って精算する →
    当たり具合と回収率の表にする。元DB を開くのは、学習データを作る段と、年ごとの確定オッズ・払戻を読む段だけ。
    途中の結果（学習データ・年ごとの予測・精算の表）は ``root`` の下に残し、止まったら続きから再開する。
    予測する時点は ``timing``（既定は当日）。オッズを足した ⑦ の買い目は、確定オッズが分かる当日の時点でだけ作る。
    """

    def __init__(self, root: Path, db_path: Path | None, progress: Callable[[str], None] | None = None,
                 reuse_datasets: bool = False, timing: PredictionTiming = DEFAULT_TIMING) -> None:
        self._root = Path(root)
        self._db_path = db_path
        self._progress = progress or (lambda message: None)
        self._timing = timing
        self._artifacts = BacktestArtifactRepository(self._root / "backtest")
        self._datasets = DatasetLoader(DatasetRepository(self._root / "datasets"), db_path, self._progress, reuse_datasets)
        self._predictor = WalkForwardPredictor(OutOfSampleRepository(self._root / "out_of_sample"), self._progress)

    def run(self, years: Sequence[int], settings_path: Path | None) -> BacktestReport:
        settings = HyperparameterSettings.load(settings_path, defaults=DEFAULT_SETTINGS_PATH)
        years = sorted(years)
        datasets = self._datasets.load(years[-1])
        schedule = WalkForwardSchedule()
        tendency = self._forecast(ForecastGroup.TENDENCY, schedule, years, datasets, PriorForecasts(), settings)
        priors = PriorForecasts(tendency)
        priors = priors.with_early(self._forecast(ForecastGroup.EARLY, schedule, years, datasets, priors, settings))
        priors = priors.with_late(self._forecast(ForecastGroup.LATE, schedule, years, datasets, priors, settings))
        finish = self._forecast(ForecastGroup.FINISH, schedule, years, datasets, priors, settings)
        early, late = priors.early, priors.late
        frames = BacktestFrames(datasets)
        settled = pd.concat([self._settled(year, frames, early, finish) for year in years], ignore_index=True)
        stage_years = list(range(schedule.first_year(ForecastGroup.EARLY), years[-1] + 1))
        all_years = list(range(TRAIN_FIRST_DAY.year, years[-1] + 1))
        all_horses = frames.horses(all_years, early, late, finish)
        horses = all_horses[all_horses["年"].isin([str(year) for year in years])]
        choices = {label: self._line_choice(label) for label in self._variants(finish)}
        candidates = {label: choice.candidates(settled) for label, choice in choices.items()}
        unlabeled = frames.unlabeled()
        return BacktestReport(
            returns=ReturnSummary().table(settled),
            finish=FinishYearMetrics().table(horses, self._finish_training_rows(years, datasets, priors)),
            stages=StageYearMetrics().table(all_horses, frames.races(all_years, early, late), stage_years),
            calibration=PlaceCalibration().table(horses),
            order_lambdas=self._order_lambdas(horses),
            line_totals={label: choices[label].line_totals(table) for label, table in candidates.items()},
            chosen_lines={label: choices[label].chosen_lines(table) for label, table in candidates.items()},
            allocation={label: choices[label].allocation(table) for label, table in candidates.items()},
            unlabeled=UnlabeledRaceTable().table(unlabeled),
            unlabeled_examples=UnlabeledRaceTable().examples(unlabeled),
            years=tuple(years), timing=self._timing, settings=settings.to_dict(),
        )

    def save_text(self, name: str, text: str) -> Path:
        """結果の表（Markdown）を ``<root>/backtest/<name>.md`` に書く。"""
        return self._artifacts.save_text(name, text)

    def _forecast(self, group: ForecastGroup, schedule: WalkForwardSchedule, years: list[int], datasets: KindDatasets,
                  priors: PriorForecasts, settings: HyperparameterSettings) -> GroupForecast:
        """その組が予測を出せる最初の年から、確かめる最後の年までの予測。"""
        group_years = list(range(schedule.first_year(group), years[-1] + 1))
        return self._predictor.predict(group, group_years, datasets, priors, self._timing, settings)

    def _variants(self, finish: GroupForecast) -> dict[str, str]:
        """買い目を作る1着の確率の列（名前 → 列）。オッズを足した ⑦ は、予測がある（当日の時点の）ときだけ。"""
        variants = {MODEL_LABEL: WIN_PROBABILITY}
        if ODDS_WIN_PROBABILITY in finish.horses.columns and finish.horses[ODDS_WIN_PROBABILITY].notna().any():
            variants[ODDS_LABEL] = ODDS_WIN_PROBABILITY
        return variants

    def _line_choice(self, label: str) -> ValueLineChoice:
        """期待値の線と券種の配分を選ぶクラス（その買い方の名前で）。"""
        return ValueLineChoice(self._renamed_rule(MODEL_MARK_RULE, label), self._renamed_rule(MODEL_VALUE_RULE, label))

    def _renamed_rule(self, rule: str, label: str) -> str:
        return rule.replace(f"（{MODEL_LABEL}）", f"（{label}）")

    def _settled(self, year: int, frames: BacktestFrames, early: GroupForecast, finish: GroupForecast) -> pd.DataFrame:
        """その年の精算した買い目（モデルの ⑦ と、あればオッズを足した ⑦）。前に精算したものがあれば読む（予測が同じなら）。"""
        tables = {label: frames.betting(year, early, finish, column) for label, column in self._variants(finish).items()}
        names = {label: f"settled_{self._fingerprint(table)}" for label, table in tables.items()}
        missing = [label for label in tables if not self._artifacts.exists(year, names[label])]
        market = self._market(year) if missing else None
        for label in missing:
            self._settle(year, tables[label], market, names[label])
        return pd.concat([self._relabeled(self._artifacts.load(year, names[label]), label) for label in tables],
                         ignore_index=True)

    def _market(self, year: int) -> YearMarket:
        """その年の確定オッズと払戻（元DB を開くのは、ここと学習データを作る段だけ）。"""
        with db.open_db(self._db_path, lock_timeout=DB_LOCK_WAIT_SECONDS) as con:
            return YearMarket.read(con, year)

    def _settle(self, year: int, betting: pd.DataFrame, market: YearMarket, name: str) -> None:
        started = time.perf_counter()
        settled = YearBetting().settle(year, betting, market.odds, market.payouts, market.flags)
        self._artifacts.save(year, name, settled)
        self._progress(f"{year}年の買い目を精算した（{len(settled)}点、{(time.perf_counter() - started) / 60:.1f}分）")

    def _relabeled(self, settled: pd.DataFrame, label: str) -> pd.DataFrame:
        """オッズを足した ⑦ の買い目は、人気順の印（モデルの ⑦ と同じもの）を落とし、買い方の名前の後ろを置き換える。"""
        if label == MODEL_LABEL:
            return settled
        kept = settled[settled[bet.RULE] != POPULARITY_MARK_RULE]
        return kept.assign(**{bet.RULE: kept[bet.RULE].map(lambda rule: self._renamed_rule(rule, label))})

    def _fingerprint(self, table: pd.DataFrame) -> str:
        return f"{int(pd.util.hash_pandas_object(table, index=False).sum()) & 0xFFFFFFFF:08x}"

    def _finish_training_rows(self, years: list[int], datasets: KindDatasets, priors: PriorForecasts) -> dict[str, int]:
        """年 → その年の ⑦ のモデルの学習データの行数（早い年ほど少ないことを、表に並べて見せるため）。"""
        kind = DevelopmentModelKind.FINISH
        labeled = datasets.labeled(kind, datasets.of(kind, priors))
        days = pd.to_datetime(labeled.ids[RACE_DATE])
        schedule = WalkForwardSchedule()
        return {
            str(year): int(((days >= pd.Timestamp(schedule.periods(ForecastGroup.FINISH, year).train_first_day))
                            & (days < pd.Timestamp(schedule.periods(ForecastGroup.FINISH, year).valid_first_day))).sum())
            for year in years
        }

    def _order_lambdas(self, horses: pd.DataFrame) -> dict[str, float]:
        """年 → ⑦ のならしの指数 λ。"""
        return {str(year): float(part[ORDER_LAMBDA].dropna().iloc[0]) for year, part in horses.groupby("年")
                if part[ORDER_LAMBDA].notna().any()}
