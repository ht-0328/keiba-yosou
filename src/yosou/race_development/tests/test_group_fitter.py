"""前半 → 後半 → 着順の組を、前の組の予測を足しながら学習して予測できるかを確かめる。"""

from __future__ import annotations

import numpy as np

from yosou.shared.dataset import RACE_ID

from ..feature import (
    CORNER4_PREDICTION,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    WIN_PROBABILITY,
)
from ..workflow import ORDER_LAMBDA


def test_early_probabilities_sum_to_one_per_race(forecasts) -> None:
    early, _, _ = forecasts
    horses = early.horses
    assert np.allclose(horses.groupby(RACE_ID)[LEADER_PROBABILITY].sum(), 1.0)
    assert horses[FRONT_PROBABILITY].between(0, 1).all()
    assert early.races[HIGH_PROBABILITY].between(0, 1).all()
    quantiles = early.races[list(FIRST_HALF_QUANTILES)].to_numpy()
    assert (np.diff(quantiles, axis=1) >= 0).all()


def test_late_and_finish_use_previous_forecasts(forecasts) -> None:
    _, late, finish = forecasts
    assert late.horses[CORNER4_PREDICTION].notna().all()
    assert np.allclose(finish.horses.groupby(RACE_ID)[WIN_PROBABILITY].sum(), 1.0)
    assert finish.horses[ORDER_LAMBDA].between(0.5, 1.0).all()
