"""荒れたレースの行だけを学ぶ決まりのテスト。合成DB（架空の1シーズン）だけを使う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db

from yosou.shared.dataset import RACE_ID, TrainingData, TrainingPeriod
from yosou.upset_level.dataset import BetType, payout_column, race_dataset_builder

from ..dataset import WildRaceRows

_PAYOUT = payout_column(BetType.TRIFECTA)


@pytest.fixture(scope="module")
def race_data(season_db: Path, season_period: TrainingPeriod) -> TrainingData:
    """架空の1シーズンのレース単位の学習データ（3連単の払戻を評価用の列に持つ。行を絞る決まりは、どの学習データにも使える）。"""
    with db.open_db(season_db) as con:
        return race_dataset_builder(con).build_training_data(season_period)


def test_3連単の払戻が線以上のレースの行だけを残す(race_data: TrainingData, season_db: Path) -> None:
    # 架空のデータには 10万円の払戻がほとんど無いので、払戻の真ん中を線にする
    line = int(race_data.evaluation[_PAYOUT].dropna().median())
    with db.open_db(season_db) as con:
        kept = WildRaceRows(line).keep(con, race_data)
    expected = set(race_data.ids.loc[race_data.evaluation[_PAYOUT].ge(line), RACE_ID])
    assert set(kept.ids[RACE_ID]) == expected
    assert 0 < len(kept) < len(race_data)


def test_空の学習データはそのまま返す(race_data: TrainingData, season_db: Path) -> None:
    empty = race_data.where(race_data.ids[RACE_ID].eq("無いレース"))
    with db.open_db(season_db) as con:
        assert len(WildRaceRows().keep(con, empty)) == 0
