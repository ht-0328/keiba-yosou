"""前の組の「学習に使っていない予測」を、年ごとに作る。"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Sequence

import pandas as pd

from yosou.shared.dataset import RACE_DATE
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings

from ..feature import GroupForecast
from ..repository import OutOfSampleRepository
from .forecast_group import ForecastGroup
from .group_fitter import GroupFitter
from .kind_datasets import KindDatasets
from .walk_forward_schedule import WalkForwardSchedule


class WalkForwardPredictor:
    """1つの組と1つの時点について、年ごとに「その年より前だけで学習し、その年を予測する」をくり返す（設計書 05 の図5・11 の決まり 11）。

    作った予測は ``OutOfSampleRepository`` に残し、同じ条件なら次からは読むだけにする。学習（``train``）と
    年ごとの確かめ（``backtest``）は、同じものを使う。``progress`` に進み具合を1行ずつ渡す。
    """

    def __init__(self, repository: OutOfSampleRepository, progress: Callable[[str], None] | None = None) -> None:
        self._repository = repository
        self._progress = progress or (lambda message: None)
        self._schedule = WalkForwardSchedule()
        self._fitter = GroupFitter()

    def predict(self, group: ForecastGroup, years: Sequence[int], datasets: KindDatasets,
                early: GroupForecast | None, late: GroupForecast | None, timing: PredictionTiming,
                settings: HyperparameterSettings) -> GroupForecast:
        """年の並びぶんの予測をつないだもの。"""
        signature = self._signature(group, timing, settings, datasets, early, late)
        parts = [self._year(group, year, datasets, early, late, timing, settings, signature) for year in years]
        return GroupForecast.concat(parts)

    def _year(self, group: ForecastGroup, year: int, datasets: KindDatasets, early: GroupForecast | None,
              late: GroupForecast | None, timing: PredictionTiming, settings: HyperparameterSettings,
              signature: str) -> GroupForecast:
        cached = self._repository.load(group.value, timing, year, signature)
        if cached is not None:
            self._progress(f"{group.label}の組 {year}年: 前に作った予測を読んだ")
            return cached
        started = time.perf_counter()
        period = self._schedule.periods(group, year)
        forecast = self._fitter.fit_predict(group, period, datasets, early, late, timing, settings)
        self._repository.save(group.value, timing, year, signature, forecast)
        minutes = (time.perf_counter() - started) / 60
        self._progress(f"{group.label}の組 {year}年: 学習して予測した（{len(forecast.horses)}頭・{len(forecast.races)}レース、{minutes:.1f}分）")
        return forecast

    def _signature(self, group: ForecastGroup, timing: PredictionTiming, settings: HyperparameterSettings,
                   datasets: KindDatasets, early: GroupForecast | None, late: GroupForecast | None) -> str:
        """予測を作った条件を表す文字列。設定・学習データの範囲・前の組の予測のどれかが変われば、違う値になる。"""
        days = datasets.horses.ids[RACE_DATE]
        parts = {
            "group": group.value, "timing": timing.value, "settings": settings.to_dict(),
            "data": [str(days.min()), str(days.max()), len(datasets.horses), len(datasets.races)],
            "early": self._forecast_hash(early), "late": self._forecast_hash(late),
        }
        return hashlib.sha1(json.dumps(parts, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def _forecast_hash(self, forecast: GroupForecast | None) -> str:
        if forecast is None:
            return ""
        horses = int(pd.util.hash_pandas_object(forecast.horses, index=False).sum())
        races = int(pd.util.hash_pandas_object(forecast.races, index=False).sum())
        return f"{horses}-{races}"
