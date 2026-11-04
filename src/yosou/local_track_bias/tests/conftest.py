"""地方の当日の馬場傾向のテストの準備。実DB は使わず、地方の合成DB（架空の地方の1シーズン。``yosou.shared.tests.local_season``）だけを使う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 合成DB import synth

from yosou.shared.tests import local_season as season


@pytest.fixture(scope="session")
def local_season_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """架空の地方の1シーズンの合成DB のパス。"""
    return synth.build_db(tmp_path_factory.mktemp("local_bias_season") / "local_season.duckdb", season.LocalSeasonBuilder().build())
