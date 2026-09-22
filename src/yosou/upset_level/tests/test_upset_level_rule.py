"""券種と荒れ具合の線引き（設計書 10）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.repository import PAYOUT_TABLES

from ..dataset import THRESHOLDS, BetType, UpsetLevel, UpsetLevelRule


def test_bet_keys_match_the_payout_tables():
    assert {bet.key for bet in BetType} == set(PAYOUT_TABLES)
    assert [bet.column_name for bet in BetType] == ["荒れ具合（単勝）", "荒れ具合（馬連）", "荒れ具合（3連複）", "荒れ具合（3連単）"]
    assert BetType.parse(" 3連単 ") is BetType.TRIFECTA
    with pytest.raises(ValueError, match="知らない券種"):
        BetType.parse("複勝")


def test_thresholds_are_the_design_values():
    assert THRESHOLDS[BetType.WIN] == (500, 1_000, 3_000)
    assert THRESHOLDS[BetType.QUINELLA] == (1_000, 3_000, 10_000)
    assert THRESHOLDS[BetType.TRIO] == (3_000, 10_000, 50_000)
    assert THRESHOLDS[BetType.TRIFECTA] == (20_000, 100_000, 500_000)
    assert UpsetLevel.labels() == ("固い", "中荒れ", "大荒れ", "超荒れ") and UpsetLevel.class_labels() == (0, 1, 2, 3)


def test_levels_follow_the_thresholds_with_the_lower_bound_included():
    rule = UpsetLevelRule()
    yen = pd.Series([100.0, 499.0, 500.0, 999.0, 1_000.0, 2_999.0, 3_000.0, 99_999.0, np.nan])
    assert rule.levels_of(BetType.WIN, yen).tolist()[:-1] == [0, 0, 1, 1, 2, 2, 3, 3]
    assert np.isnan(rule.levels_of(BetType.WIN, yen).iloc[-1])
    assert rule.level_of(BetType.TRIFECTA, 19_999) is UpsetLevel.SOLID
    assert rule.level_of(BetType.TRIFECTA, 500_000) is UpsetLevel.HUGE
    assert rule.level_of(BetType.TRIFECTA, None) is None
    assert rule.is_upset_or_more(BetType.QUINELLA, pd.Series([999.0, 1_000.0, np.nan])).tolist() == [False, True, False]
