"""CoefficientStore（係数の JSON の読み書き）のテスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 地方の推奨買目.coefficient_store import CoefficientStore
from 地方の推奨買目.position_coefficients import PositionCoefficients


def test_書いて読むと同じ係数_無ければ分かる誤り(tmp_path: Path):
    store = CoefficientStore(tmp_path / "係数.json")
    with pytest.raises(FileNotFoundError, match=r"fit\.py"):
        store.load()
    coefficients = PositionCoefficients({"log_p1_lgb": 1.2, "log_s": -0.3}, {"log_p1": 0.9}, {"log_p1": 0.8, "log_m3": 0.5})
    store.save(coefficients, {"年": [2024, 2025]})
    assert store.load() == coefficients
    assert store.meta() == {"年": [2024, 2025]}
    assert list(store.load().vector(0)) == [1.2, -0.3]
