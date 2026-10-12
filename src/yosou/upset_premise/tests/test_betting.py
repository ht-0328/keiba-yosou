"""買い方（一律・甲・乙・丙）と組の確率のテスト。架空の値だけを使う。"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pytest

from ..betting import FlatPlan, FormationPlan, ObiStakePlan, RaceHorses, trifecta_probability, trio_probability


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


def test_線を10万円に下げると線に要る金額で買う() -> None:
    horses = _horses()
    odds = {order: 250.0 for order in permutations(range(1, 11), 3)}
    plan = ObiStakePlan(ordered=True, line_yen=100_000)
    tickets = plan.tickets(horses, odds)
    assert plan.name == "甲 当たれば10万円以上（3連単）"
    assert all(stake == 400 for _, stake in tickets)  # 10万 ÷ 250倍 = 400円
    assert sum(stake for _, stake in tickets) == 10_000


def test_2着3着の重みを渡したHarvilleの式も全部の組で合計1() -> None:
    win = {1: 0.5, 2: 0.3, 3: 0.2}
    place = {1: 0.9, 2: 0.6, 3: 0.3}
    total = sum(trifecta_probability(win, *order, place=place) for order in permutations(win, 3))
    assert total == pytest.approx(1.0)
    # 1着の確率は win のまま、2着・3着は place の比で決まる
    assert trifecta_probability(win, 1, 2, 3, place=place) == pytest.approx(0.5 * 0.6 / 0.9 * 0.3 / 0.3)


def test_2着3着の重みは今の予想の3着以内があれば荒れる前提との平均() -> None:
    numbers = np.array([1, 2, 3])
    plain = RaceHorses("r1", numbers, np.array([0.5, 0.3, 0.2]), np.array([0.8, 0.5, 0.2]))
    assert plain.place_of() == {1: 0.8, 2: 0.5, 3: 0.2}
    both = RaceHorses("r1", numbers, np.array([0.5, 0.3, 0.2]), np.array([0.8, 0.5, 0.2]), np.array([0.6, 0.7, 0.4]))
    assert both.place_of() == pytest.approx({1: 0.7, 2: 0.6, 3: 0.3})
    with pytest.raises(ValueError):
        RaceHorses("r1", numbers, np.array([0.5, 0.3, 0.2]), np.array([0.8, 0.5, 0.2]), np.array([0.6, 0.7]))


def test_一律は1000倍以上の組を組の確率の高い順に一律の金額で予算ぶん買う() -> None:
    horses = _horses()
    odds = {order: 1_500.0 for order in permutations(range(1, 11), 3)}
    odds[(1, 2, 3)] = 800.0  # 1,000倍未満なので買わない
    plan = FlatPlan()
    tickets = plan.tickets(horses, odds)
    assert plan.name == "一律 1,000倍以上（3連単・1点100円・100点）"
    assert len(tickets) == 100 and all(stake == 100 for _, stake in tickets)
    assert (1, 2, 3) not in [combo for combo, _ in tickets]
    win, place = horses.win_of(), horses.place_of()
    probabilities = [trifecta_probability(win, *combo, place=place) for combo, _ in tickets]
    assert probabilities == sorted(probabilities, reverse=True)  # 組の確率の高い順
    assert probabilities[0] == max(trifecta_probability(win, *combo, place=place) for combo in odds if odds[combo] >= 1_000)
    assert len(FlatPlan(300).tickets(horses, odds)) == 33 and len(FlatPlan(500).tickets(horses, odds)) == 20
    with pytest.raises(ValueError):
        FlatPlan(250)
