"""この予想のテストの準備。実DB は使わず、合成DB（架空の1シーズン）だけを使う。

合成DB（``season_db``）・速い設定（``fast_settings_path``）・期間（``season_period``）は
``src/yosou/conftest.py``。ここには、この予想の組み立てで作るものを置く。

| フィクスチャ | 中身 |
|---|---|
| ``longshot_db`` | 架空の1シーズンに、全レースの複勝オッズ（まとまり M の材料）を足した合成DB |
| ``no_place_odds_db`` | 架空の1シーズンから、複勝オッズ（確定前の 1R の締め切り前の断面）を抜いた合成DB |
| ``training_data`` | この予想の学習データ（穴馬の行・3着以内・特徴量 A〜M・穴馬の区分） |
| ``trained`` | 学習の流れを1回通した結果（モデルを置いたフォルダと ``TrainingReport``） |
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from 共通 import db, keys
from 合成DB import synth

from yosou.shared.dataset import TrainingData, TrainingPeriod
from yosou.shared.evaluation import TrainingReport
from yosou.shared.tests import synthetic_season as season
from yosou.shared.workflow import SegmentedTraining

from ..dataset import dataset_builder
from ..setting import DEFAULT_SETTINGS_PATH
from ..workflow import SEGMENTS, TIMINGS

#: 複勝オッズの親と子の表。
_HEADER, _PLACE = "o1", "o1__複勝オッズ"
#: 確定前のレース（締め切り前の断面を入れる）と、その断面の発表月日時分。
_FUTURE_RACE_IDS = {season.CARD_RACE_ID, season.ENTRY_LIST_RACE_ID, season.JUMP_CARD_RACE_ID}
_ANNOUNCED = "01110930"


def _race_id(row: dict[str, str]) -> str:
    return "".join(row[name] for name in keys.RACE_KEY)


def _odds_header(race_row: dict[str, str]) -> tuple[str, dict[str, str]]:
    """確定したレースは確定の断面（データ区分 5）、確定前のレースは締め切り前の断面（データ区分 1）。"""
    if _race_id(race_row) in _FUTURE_RACE_IDS:
        return _HEADER, synth.odds_header(race_row, _HEADER, stage="1", announced=_ANNOUNCED)
    return _HEADER, synth.odds_header(race_row, _HEADER)


def _place_odds(race_row: dict[str, str], runner: dict[str, str], seq: int) -> tuple[str, dict[str, str]]:
    """1頭の複勝オッズ。単勝オッズの 3分の1 を最低、その 2倍を最高にする（単勝オッズの無い確定前の馬は馬番から作る）。"""
    win_tenths = int(runner["単勝オッズ"] or 0) or 15 + 20 * int(runner["馬番"])
    low = max(11, win_tenths // 3)
    announced = _ANNOUNCED if _race_id(race_row) in _FUTURE_RACE_IDS else "00000000"
    return _PLACE, synth.range_odds_row(race_row, _PLACE, runner["馬番"], low, 2 * low, seq=seq, announced=announced)


def with_place_odds(sample: synth.Sample) -> synth.Sample:
    """``sample`` の全レース（馬番の決まっている馬）に複勝オッズを足した、新しい行の束（``sample`` は変えない）。

    すでにオッズの断面があるレース（共通の架空のシーズンの、確定前の 1R）は、そのまま使って足さない。
    """
    priced = {_race_id(row) for table, row in sample.odds if table == _HEADER}
    races = {_race_id(row): row for row in sample.ra if _race_id(row) not in priced}
    numbered = [runner for runner in sample.se if _race_id(runner) in races
                and runner["馬番"].strip().isdigit() and int(runner["馬番"]) > 0]
    headers = [_odds_header(row) for row in races.values()]
    rows = [_place_odds(races[_race_id(runner)], runner, seq) for seq, runner in enumerate(numbered, start=1)]
    return replace(sample, odds=[*sample.odds, *headers, *rows])


@pytest.fixture(scope="session")
def longshot_db(season_sample: synth.Sample, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """架空の1シーズンに、全レースの複勝オッズを足した合成DB のパス。"""
    return synth.build_db(tmp_path_factory.mktemp("longshot-season") / "season.duckdb", with_place_odds(season_sample))


@pytest.fixture(scope="session")
def no_place_odds_db(season_sample: synth.Sample, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """架空の1シーズンから、オッズの行（確定前の 1R の締め切り前の複勝オッズ）を抜いた合成DB のパス。"""
    return synth.build_db(tmp_path_factory.mktemp("no-place-odds") / "season.duckdb", replace(season_sample, odds=[]))


@pytest.fixture(scope="session")
def training_data(longshot_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンの学習データ（穴馬の行だけ）。"""
    with db.open_db(longshot_db) as con:
        return dataset_builder(con).build_training_data(season_period)


@pytest.fixture(scope="session")
def trained(longshot_db: Path, fast_settings_path: Path, season_period: TrainingPeriod,
            tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[tuple[str, TrainingReport]]]:
    """区分（中穴・大穴）ごとの学習を1回通して、モデルを置いたフォルダと（区分, 学習の結果）の並びを返す。"""
    models = tmp_path_factory.mktemp("longshot-models")
    with db.open_db(longshot_db) as con:
        training = SegmentedTraining(SEGMENTS, dataset_builder(con), season_period, models, TIMINGS,
                                     DEFAULT_SETTINGS_PATH)
        training_data = training.read_training_data()
    return models, training.train(training_data, fast_settings_path)
