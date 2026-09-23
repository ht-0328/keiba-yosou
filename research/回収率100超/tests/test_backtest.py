"""回収率・信頼区間・期間の区切りのテスト。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 回収率100超.analysis.backtest import Payback, PaybackInterval, WalkForwardYears


def test_回収率は払戻の合計を賭けた金で割った値() -> None:
    payback = Payback(pd.Series([0, 0, 300, 100]))
    assert payback.rate == pytest.approx(100.0)
    assert payback.hit_rate == pytest.approx(0.5)


def test_買い目が無ければ回収率は_NaN() -> None:
    assert np.isnan(Payback(pd.Series([], dtype=float)).rate)


def test_信頼区間は下限が上限以下になる() -> None:
    day = pd.Series(["2026-01-01"] * 5 + ["2026-01-02"] * 5)
    payout = pd.Series([0, 0, 0, 0, 500, 0, 300, 0, 0, 200])
    low, high = PaybackInterval(rounds=200).of(day, payout)
    assert low <= high


def test_ウォークフォワードは直前の年を学習から外す() -> None:
    year = np.array([2020, 2021, 2022, 2023])
    splits = list(WalkForwardYears(year, 2022, 2023))
    assert [s.test_year for s in splits] == [2022, 2023]
    first = splits[0]
    assert list(year[first.fit]) == [2020]
    assert list(year[first.valid]) == [2021]
    assert list(year[first.test]) == [2022]
