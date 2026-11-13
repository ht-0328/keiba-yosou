"""この予想のテストの準備。実DB は使わず、合成DB（架空の WIN5）だけを使う。

| フィクスチャ | 中身 |
|---|---|
| ``win5_sample`` | 架空の WIN5 の行の束と、答え（馬番ごとの単勝オッズ・当たり組）を持つ ``Win5Sample`` |
| ``win5_db`` | その行を入れた合成DB のパス |
| ``estimator`` | 架空の過去の WIN5 で作った配当の見積もりの式 |
"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import db
from 合成DB import synth

from ..payout import FEATURE_COLUMNS, PayoutEstimator, PayoutTrainingRows
from ..repository import Win5HistoryRepository
from ..repository.win5_columns import PAYOUT
from .win5_sample import FORECAST_DAY, Win5Sample


@pytest.fixture(scope="session")
def win5_sample() -> Win5Sample:
    builder = Win5Sample()
    builder.build()
    return builder


@pytest.fixture(scope="session")
def win5_db(win5_sample: Win5Sample, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return synth.build_db(tmp_path_factory.mktemp("win5") / "win5.duckdb", win5_sample.sample)


@pytest.fixture(scope="session")
def estimator(win5_db: Path) -> PayoutEstimator:
    with db.open_db(win5_db) as con:
        history = Win5HistoryRepository(con).read(FORECAST_DAY)
    rows = PayoutTrainingRows().of(history)
    return PayoutEstimator.fit(rows[list(FEATURE_COLUMNS)], rows[PAYOUT])
