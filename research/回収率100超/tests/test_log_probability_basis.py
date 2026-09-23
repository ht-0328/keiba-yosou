"""折れ線の基底のテスト。"""

from __future__ import annotations

import numpy as np
import pytest

from 回収率100超.analysis.market import LogProbabilityBasis


def test_列の数は_1_足す_節の数() -> None:
    basis = LogProbabilityBasis((-5.0, -3.0))
    assert basis.width == 3
    assert basis.build(np.array([0.1, 0.5])).shape == (2, 3)


def test_最初の列は_log_の確率() -> None:
    built = LogProbabilityBasis((-3.0,)).build(np.array([0.5]))
    assert built[0, 0] == pytest.approx(np.log(0.5))


def test_節より小さい確率では折れ線の列が0になる() -> None:
    built = LogProbabilityBasis((-3.0,)).build(np.array([np.exp(-5.0)]))
    assert built[0, 1] == 0.0


def test_確率が0でも計算できる() -> None:
    assert np.isfinite(LogProbabilityBasis().build(np.array([0.0]))).all()
