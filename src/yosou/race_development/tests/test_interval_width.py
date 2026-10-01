"""契約: 80% の幅の倍率は、検証データで下と上にそれぞれ 10% ずつ外れるように決まり、真ん中の値は変えない。
倍率はモデルのファイルの隣に書かれ、無ければ元のまま（1.0）として読む。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..ml_model import IntervalWidth, IntervalWidthFitter

#: 標準正規分布の 90% の点。
_Z90 = 1.2816


def test_fitter_widens_a_too_narrow_interval_to_ten_percent_each_side() -> None:
    """幅が半分の狭さなら、倍率はおおよそ 2 になり、広げた幅に 80% ほど入る。"""
    rng = np.random.default_rng(20260930)
    actual = rng.normal(0.0, 1.0, 20000)
    half = _Z90 / 2
    quantiles = np.column_stack([np.full(actual.size, -half), np.zeros(actual.size), np.full(actual.size, half)])
    width = IntervalWidthFitter().fit(quantiles, actual)
    assert 1.9 <= width.lower <= 2.1
    assert 1.9 <= width.upper <= 2.1
    low, middle, high = width.apply(quantiles).T
    assert np.allclose(middle, 0.0)
    assert abs(np.mean((actual >= low) & (actual <= high)) - 0.8) < 0.02


def test_fitter_sets_each_side_separately() -> None:
    """上にだけ外れやすいときは、上の倍率だけが大きくなる。"""
    rng = np.random.default_rng(1)
    actual = rng.exponential(1.0, 20000)
    quantiles = np.column_stack([np.full(actual.size, 0.105), np.full(actual.size, 0.69), np.full(actual.size, 1.2)])
    width = IntervalWidthFitter().fit(quantiles, actual)
    assert width.upper > 1.5
    assert width.lower < 1.1


def test_apply_sorts_crossed_quantiles_first() -> None:
    crossed = np.array([[2.0, 1.0, 3.0]])
    assert IntervalWidth(2.0, 1.0).apply(crossed).tolist() == [[0.0, 2.0, 3.0]]


def test_width_is_saved_next_to_the_model_and_defaults_to_one(tmp_path: Path) -> None:
    model_path = tmp_path / "lightgbm_quantile.joblib"
    assert IntervalWidth.load(model_path) == IntervalWidth()
    IntervalWidth(1.25, 1.4).save(model_path)
    assert IntervalWidth.load(model_path) == IntervalWidth(1.25, 1.4)
