"""展開の予想の年ごとの確かめで、まだ作っていない年の予測を作り足す。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from yosou.race_development.feature import GroupForecast, PriorForecasts
from yosou.race_development.repository import DatasetRepository, OutOfSampleRepository
from yosou.race_development.workflow import DatasetLoader, ForecastGroup, GroupFitter, KindDatasets, WalkForwardSchedule
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings

#: 作り足した予測に付ける、作った条件の印。展開の予想の backtest の条件とは一致しないので、backtest は読まずに作り直す。
FILLED_SIGNATURE = "pace_check fill"
#: 作り足す組（後の組は、前の組の全部の年の予測を材料にする）。
_GROUPS = (ForecastGroup.TENDENCY, ForecastGroup.EARLY, ForecastGroup.LATE)


class ForecastFiller:
    """``<root>/out_of_sample/`` に、組の最初の年から ``last_year`` までで抜けている年の予測を、年ごとの確かめと同じ部品
    （``GroupFitter``・``WalkForwardSchedule``）で作り足す。

    例: 木曜の確かめは 2025年までしか回していないので、2026年の木曜の予測が無い。その年のモデルは、前の年の9月までで学習し、
    10〜12月で早期終了するので、その年を学習に使っていない（展開の設計書 11 の決まり 11）。前の組の予測は、残っている予測を使う。
    学習データは展開の予想が残した ``<root>/datasets/``（元DB は開かない）。
    """

    def __init__(self, root: Path, settings: HyperparameterSettings,
                 progress: Callable[[str], None] | None = None) -> None:
        self._root = Path(root)
        self._settings = settings
        self._progress = progress or (lambda message: None)
        self._repository = OutOfSampleRepository(self._root / "out_of_sample")
        self._schedule = WalkForwardSchedule()
        self._fitter = GroupFitter()

    def missing(self, timing: PredictionTiming, last_year: int) -> dict[str, list[int]]:
        """組の名前 → 抜けている年。"""
        return {group.label: [year for year in self._years(group, last_year) if not self._has(group, timing, year)]
                for group in _GROUPS}

    def fill(self, timing: PredictionTiming, last_year: int) -> list[str]:
        """抜けている年を作り足し、作ったもの（組と年）を返す。"""
        if not any(self.missing(timing, last_year).values()):
            return []
        loader = DatasetLoader(DatasetRepository(self._root / "datasets"), None, self._progress, reuse_saved=True)
        datasets = loader.load(last_year)
        priors, made = PriorForecasts(), []
        for group in _GROUPS:
            forecast = GroupForecast.concat([self._year(group, year, timing, datasets, priors, made)
                                             for year in self._years(group, last_year)])
            priors = self._with(priors, group, forecast)
        return made

    def _year(self, group: ForecastGroup, year: int, timing: PredictionTiming, datasets: KindDatasets,
              priors: PriorForecasts, made: list[str]) -> GroupForecast:
        """その年の予測（残っていれば読み、無ければ学習して作り、残す）。"""
        stored = self._repository.stored(group.value, timing, year)
        if stored is not None:
            return stored
        self._progress(f"{group.label}の組 {year}年（{timing.label}）: 学習して予測しています …")
        period = self._schedule.periods(group, year)
        forecast = self._fitter.fit_predict(group, period, datasets, priors, timing, self._settings)
        self._repository.save(group.value, timing, year, FILLED_SIGNATURE, forecast)
        made.append(f"{group.label} {year}年")
        return forecast

    def _has(self, group: ForecastGroup, timing: PredictionTiming, year: int) -> bool:
        return year in self._repository.years(group.value, timing)

    def _years(self, group: ForecastGroup, last_year: int) -> list[int]:
        return list(range(self._schedule.first_year(group), last_year + 1))

    def _with(self, priors: PriorForecasts, group: ForecastGroup, forecast: GroupForecast) -> PriorForecasts:
        """前の組の予測の束に、その組の予測を足したもの。"""
        if group is ForecastGroup.TENDENCY:
            return PriorForecasts(forecast)
        if group is ForecastGroup.EARLY:
            return priors.with_early(forecast)
        return priors.with_late(forecast)
