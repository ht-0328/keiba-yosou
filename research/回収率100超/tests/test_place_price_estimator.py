"""複勝の想定払戻倍率のテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd
import pytest

from 回収率100超.analysis.ticket import PlacePriceEstimator


def test_的中した馬から倍率を学び_発表オッズに掛ける() -> None:
    lowest = pd.Series([2.5, 2.5, 2.5, 2.5])
    payout = pd.Series([500, 500, 0, 0])          # 的中した2頭は 5.0倍（発表の2倍）
    placed = pd.Series([1, 1, 0, 0])
    estimator = PlacePriceEstimator().fit(lowest, payout, placed)
    assert estimator.estimate(pd.Series([2.5])).iloc[0] == pytest.approx(5.0)


def test_学ぶ前に使うとエラーになる() -> None:
    with pytest.raises(RuntimeError):
        PlacePriceEstimator().estimate(pd.Series([2.0]))
