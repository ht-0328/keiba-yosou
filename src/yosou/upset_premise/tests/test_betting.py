"""買い方（甲・乙・丙）と組の確率のテスト。架空の値だけを使う。"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pytest

from ..betting import FormationPlan, ObiStakePlan, RaceHorses, trifecta_probability, trio_probability


def _horses(count: int = 10) -> RaceHorses:
    numbers = np.arange(1, count + 1)
    win = np.linspace(2.0, 1.0, count)
    return RaceHorses("r1", numbers, win / win.sum(), np.linspace(0.6, 0.1, count))


def test_Harvilleの3連単の確率は全部の組で合計1() -> None:
    win = {1: 0.5, 2: 0.3, 3: 0.2}
    total = sum(trifecta_probability(win, *order) for order in permutations(win, 3))
    assert total == pytest.approx(1.0)
    assert trio_probability(win, (1, 2, 3)) == pytest.approx(1.0)


def test_乙は3と5と8頭のフォーメーションで上位10点を厚くしトリガミを買わない() -> None:
    horses = _horses()
    odds = {order: 500.0 for order in permutations(range(1, 11), 3)}
    odds[(1, 2, 3)] = 20.0  # 300円でも 6,000円にしかならない組
    tickets = FormationPlan().tickets(horses, odds)
    combos = [combo for combo, _ in tickets]
    assert len(combos) == 72 - 1 and (1, 2, 3) not in combos
    stakes = [stake for _, stake in tickets]
    assert stakes.count(300) == 9 and stakes.count(100) == 62  # (1,2,3) は上位10点の1つだった
    assert sum(stakes) <= 10_000


def test_甲は帯に要る金額で買い予算1万円に収める() -> None:
    horses = _horses()
    odds = {order: 2_000.0 for order in permutations(range(1, 11), 3)}
    odds[(1, 2, 3)] = 900.0  # 帯に 1,200円要るので買わない
    tickets = ObiStakePlan(ordered=True).tickets(horses, odds)
    assert all(stake == 500 for _, stake in tickets)  # 100万 ÷ 2,000倍 = 500円
    assert len(tickets) == 20 and (1, 2, 3) not in [combo for combo, _ in tickets]
    assert all(odds[combo] * stake >= 1_000_000 for combo, stake in tickets)


def test_丙は3連複の組を小さい順の馬番で作る() -> None:
    horses = _horses()
    odds = {tuple(sorted(order)): 1_000.0 for order in permutations(range(1, 11), 3)}
    tickets = ObiStakePlan(ordered=False).tickets(horses, odds)
    assert tickets and all(list(combo) == sorted(combo) for combo, _ in tickets)
    assert sum(stake for _, stake in tickets) == 10_000
