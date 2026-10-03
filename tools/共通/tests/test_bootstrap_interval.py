"""回収率の推定幅（``BootstrapInterval``）のテスト。値は架空。"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval


def test_幅は実際の回収率をはさみ日が多いほど狭い() -> None:
    days = pd.Series(np.arange(300) % 30)
    payout = pd.Series([250.0 if i % 2 == 0 else 0.0 for i in range(300)])  # 回収率 125%
    low, high = BootstrapInterval(rounds=200).of(days, pd.Series(100.0, index=payout.index), payout)
    assert low <= 1.25 <= high
    few_low, few_high = BootstrapInterval(rounds=200).of(days[:60], pd.Series(100.0, index=payout.index[:60]), payout[:60])
    assert few_high - few_low >= high - low


def test_買った点が無ければ欠損値() -> None:
    low, high = BootstrapInterval().of(pd.Series([], dtype=int), pd.Series([], dtype=float), pd.Series([], dtype=float))
    assert math.isnan(low) and math.isnan(high)
