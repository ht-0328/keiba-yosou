"""レース選び（予想が見た 1,000倍以上になる確率・点数）のテスト。架空の値だけを使う。"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pytest

from ..betting import RaceHorses
from ..selection import BigPayoutChance, RaceSelectionScore


def _horses() -> RaceHorses:
    numbers = np.arange(1, 6)
    win = np.array([0.5, 0.2, 0.15, 0.1, 0.05])
    return RaceHorses("r1", numbers, win, np.linspace(0.8, 0.2, 5))


def test_予想が見た確率は1000倍以上の組の確率の合計で全部なら1() -> None:
    horses = _horses()
    every = {order: 1_500.0 for order in permutations(range(1, 6), 3)}
    assert BigPayoutChance().of(horses, every) == pytest.approx(1.0)
    none = {order: 500.0 for order in permutations(range(1, 6), 3)}
    assert BigPayoutChance().of(horses, none) == 0.0
    # 1番人気が1着の組は全部 1,000倍未満なら、残りは 1 − 0.5
    mixed = {order: (500.0 if order[0] == 1 else 2_000.0) for order in permutations(range(1, 6), 3)}
    assert BigPayoutChance().of(horses, mixed) == pytest.approx(0.5)
    assert BigPayoutChance().of(horses, {}) == 0.0  # オッズが無ければ合計に入らない


def test_点数は荒れ具合の確率と予想が見た確率の平均で無ければ荒れ具合だけ() -> None:
    assert RaceSelectionScore().of(0.5, 0.3) == pytest.approx(0.4)
    assert RaceSelectionScore().of(0.5, None) == pytest.approx(0.5)
