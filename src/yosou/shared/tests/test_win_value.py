"""1着の基準（``WinBaseline``）と、単勝の期待値・期待度（``win_value``）のテスト。値は架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ..dataset import WinBaseline
from ..feature import PredictionTiming
from ..win_value import HIGH, LOW, WIN_VALUE, ExpectationLevel, WinExpectedValue


def test_win_baseline_is_the_logit_of_the_market_win_rate() -> None:
    entries = pd.DataFrame({"race_id": ["R", "R", "R", "S", "S"], "win_odds": [2.0, 4.0, 4.0, np.nan, np.nan]})
    logit = WinBaseline().build(entries)
    # 1/2 : 1/4 : 1/4 をそろえると 0.5・0.25・0.25
    assert 1.0 / (1.0 + np.exp(-logit.iloc[0])) == pytest.approx(0.5)
    assert 1.0 / (1.0 + np.exp(-logit.iloc[1])) == pytest.approx(0.25)
    # オッズの無い馬は 1 ÷ 頭数
    assert 1.0 / (1.0 + np.exp(-logit.iloc[3])) == pytest.approx(0.5)
    assert WinBaseline().known_from is PredictionTiming.DAY_BEFORE


def test_win_expected_value_is_probability_times_odds() -> None:
    values = WinExpectedValue().of(pd.Series([0.21, 0.5, 0.1], index=[7, 8, 9]), pd.Series([6.0, np.nan, 0.0], index=[7, 8, 9]))
    assert values.name == WIN_VALUE and values.index.tolist() == [7, 8, 9]
    assert values.iloc[0] == pytest.approx(1.26)
    assert values.iloc[1:].isna().all()


def test_expectation_level_is_high_or_low_at_the_fixed_line() -> None:
    level = ExpectationLevel()
    assert level.of(1.26) == HIGH and level.of(1.0) == HIGH
    assert level.of(0.99) == LOW
    assert level.of(float("nan")) is None and level.of(None) is None
