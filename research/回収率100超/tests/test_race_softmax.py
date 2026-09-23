"""レース内で合計1にする部品のテスト。"""

from __future__ import annotations

import numpy as np
import pytest

from 回収率100超.analysis.market import RaceSoftmax


def test_レースごとに合計1になる() -> None:
    race_index = np.array([0, 0, 0, 1, 1])
    probability = RaceSoftmax(race_index).to_probability(np.array([1.0, 2.0, 3.0, 0.5, 0.5]))
    assert probability[:3].sum() == pytest.approx(1.0)
    assert probability[3:].sum() == pytest.approx(1.0)


def test_同じ点数なら同じ確率になる() -> None:
    probability = RaceSoftmax(np.array([0, 0])).to_probability(np.array([7.0, 7.0]))
    assert probability == pytest.approx(np.array([0.5, 0.5]))


def test_点数が大きくても桁あふれしない() -> None:
    probability = RaceSoftmax(np.array([0, 0])).to_probability(np.array([1000.0, 999.0]))
    assert np.isfinite(probability).all()
    assert probability.sum() == pytest.approx(1.0)
