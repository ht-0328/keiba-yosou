"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う（keiba-yosou の決まり）。

共通の合成DB の行（``season_sample``）には、コーナー通過順位の表が無く、前3ハロン・後3ハロンがどのレースも同じ値なので、
先頭の馬とペースの正解が作れない。ここでは、その行の束に、コーナー通過順位（着順の並びをそのまま最初のコーナーの並びにする）と、
レースごとに違う前半・後半のタイムを足してから、この予想のための合成DB を作る。

| フィクスチャ | 中身 |
|---|---|
| ``development_db`` | この予想のための合成DB のパス |
| ``datasets`` | 1頭ごと・1レースごとの学習データ（``KindDatasets``） |
| ``forecasts`` | 前半・後半・着順の組を、決めた期間で学習して予測した結果（3つの ``GroupForecast``） |
"""

from __future__ import annotations

import copy
import random
from datetime import date
from pathlib import Path

import pytest

from 共通 import db
from 合成DB import synth

from yosou.shared.dataset import TrainingPeriod
from yosou.shared.feature import PredictionTiming
from yosou.shared.setting import HyperparameterSettings

from ..dataset import horse_dataset_builder, race_dataset_builder
from ..feature.history import pace_baseline
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import ForecastGroup, GroupFitter, KindDatasets, YearPeriod

#: テストでだけ使う、基準に要るレースの数（架空のシーズンは短く、本番の 30 レースでは春まで基準が作れないため）。
TEST_MIN_RACES = 5
#: 前半・後半のタイムのくじの種と、ずらす幅（0.1秒の単位）。
_SEED = 20260926
_SPREAD = 15
#: 組ごとの学習・検証・予測の期間（架空のシーズン 2023年10月〜2024年12月の中で、前の組の予測が後の組の学習に足りるように）。
EARLY_PERIOD = YearPeriod(date(2024, 1, 1), date(2024, 3, 1), date(2024, 4, 1), date(2025, 1, 1))
LATE_PERIOD = YearPeriod(date(2024, 4, 1), date(2024, 6, 15), date(2024, 8, 1), date(2025, 1, 1))
FINISH_PERIOD = YearPeriod(date(2024, 8, 1), date(2024, 10, 1), date(2024, 11, 1), date(2025, 1, 1))


@pytest.fixture(scope="session")
def development_db(season_sample: synth.Sample, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """コーナー通過順位と、レースごとに違う前半・後半のタイムを足した合成DB。"""
    sample = copy.deepcopy(season_sample)
    rng = random.Random(_SEED)
    runners_by_race = _runners_by_race(sample)
    for race in sample.ra:
        _vary_halves(race, rng)
        order = _passing_order(runners_by_race.get(_race_key(race), []))
        if order:
            sample.corners.append(synth.corner(race, 1, 3, order))
            sample.corners.append(synth.corner(race, 2, 4, order))
    return synth.build_db(tmp_path_factory.mktemp("development") / "development.duckdb", sample)


@pytest.fixture(scope="session")
def datasets(development_db: Path, season_period: TrainingPeriod) -> KindDatasets:
    """1頭ごと・1レースごとの学習データ。基準に要るレースの数だけ、テストの間は小さくする。"""
    original = pace_baseline.MIN_RACES
    pace_baseline.MIN_RACES = TEST_MIN_RACES
    try:
        with db.open_db(development_db) as con:
            horses = horse_dataset_builder(con).build_training_data(season_period)
            races = race_dataset_builder(con).build_training_data(season_period)
    finally:
        pace_baseline.MIN_RACES = original
    return KindDatasets(horses, races)


@pytest.fixture(scope="session")
def forecasts(datasets: KindDatasets, fast_settings_path: Path):
    """前半 → 後半 → 着順の順に、決めた期間で学習して予測した結果（前半, 後半, 着順）。"""
    settings = HyperparameterSettings.load(fast_settings_path, defaults=DEFAULT_SETTINGS_PATH)
    fitter, timing = GroupFitter(), PredictionTiming.RACE_DAY
    early = fitter.fit_predict(ForecastGroup.EARLY, EARLY_PERIOD, datasets, None, None, timing, settings)
    late = fitter.fit_predict(ForecastGroup.LATE, LATE_PERIOD, datasets, early, None, timing, settings)
    finish = fitter.fit_predict(ForecastGroup.FINISH, FINISH_PERIOD, datasets, early, late, timing, settings)
    return early, late, finish


def _race_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[column] for column in synth.KEY_COLUMNS)


def _runners_by_race(sample: synth.Sample) -> dict[tuple[str, ...], list[dict[str, str]]]:
    runners: dict[tuple[str, ...], list[dict[str, str]]] = {}
    for runner in sample.se:
        runners.setdefault(_race_key(runner), []).append(runner)
    return runners


def _passing_order(runners: list[dict[str, str]]) -> str:
    """着順の並びを、最初のコーナーの通過順位の文字列にする（合成DB の1頭ごとのコーナーの順位は着順と同じ）。"""
    placed = [runner for runner in runners if int(runner["確定着順"]) > 0]
    ordered = sorted(placed, key=lambda runner: int(runner["確定着順"]))
    return ",".join(str(int(runner["馬番"])) for runner in ordered)


def _vary_halves(race: dict[str, str], rng: random.Random) -> None:
    """前3ハロン・後3ハロンを、レースごとに少しずつ変える（基準の標準偏差が 0 にならないように）。"""
    race["前3ハロン"] = f"{350 + rng.randint(-_SPREAD, _SPREAD):03d}"
    race["後3ハロン"] = f"{350 + rng.randint(-_SPREAD, _SPREAD):03d}"
