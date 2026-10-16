"""近走の文のテストの準備。実DB は使わず、架空の1シーズンの合成DB（``yosou.shared.tests.synthetic_season``）を使う。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 合成DB import synth

from yosou.shared.tests import synthetic_season as season


@pytest.fixture(scope="session")
def season_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """架空の1シーズンの合成DB のパス（80頭がシーズンを通して走る）。"""
    return synth.build_db(tmp_path_factory.mktemp("season") / "season.duckdb", season.SeasonBuilder().build())
