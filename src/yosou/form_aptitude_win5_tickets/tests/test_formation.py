"""買い目（並べ方・フォーメーション・組の値・組み方の探索・買う日の判断）のテスト。"""

from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_NO

from ..formation import (
    BudgetTierJudge,
    BudgetTiers,
    DayDecision,
    FavoriteProduct,
    Formation,
    FormationSearch,
    FormationValue,
    LegOrdering,
)
from ..leg import EDGE, MARKET, SHARE
from ..payout import CARRY_LOG, INVERSE_LOG, PayoutEstimator, PayoutPool

#: テストの式（傾き 1・切片 3.5・補正 1.1）。
ESTIMATOR = PayoutEstimator((1.0, 0.5), 3.5, 1.1, 0.4, 100)
POOL = PayoutPool(votes=2_000_000, carry=0)


def _leg(shares: list[float], markets: list[float]) -> pd.DataFrame:
    share = np.array(shares) / sum(shares)
    market = np.array(markets) / sum(markets)
    return pd.DataFrame({HORSE_NO: range(1, len(shares) + 1), SHARE: share, MARKET: market, EDGE: share / market})


def _legs() -> list[pd.DataFrame]:
    rng = np.random.default_rng(7)
    sizes = (4, 3, 4, 2, 3)
    return [_leg(list(rng.uniform(0.05, 1.0, size)), list(rng.uniform(0.05, 1.0, size))) for size in sizes]


def _combo_values(legs: list[pd.DataFrame]) -> dict[tuple[int, ...], tuple[float, float]]:
    """組 → （当たる確率, 当たる確率 × 見積もりの配当）を、1組ずつ Python で数えたもの。"""
    horses = [{int(n): (s, m) for n, s, m in zip(leg[HORSE_NO], leg[SHARE], leg[MARKET], strict=True)} for leg in legs]
    values = {}
    for combo in itertools.product(*[sorted(each) for each in horses]):
        probability = math.prod(each[number][0] for each, number in zip(horses, combo, strict=True))
        market = math.prod(each[number][1] for each, number in zip(horses, combo, strict=True))
        raw = math.exp(ESTIMATOR.intercept + ESTIMATOR.slopes[0] * -math.log(market)) * ESTIMATOR.smear
        payout = POOL.money / (POOL.money / raw + 1.0)
        values[combo] = (probability, probability * payout)
    return values


def _brute_payout(legs: list[pd.DataFrame], formation: Formation) -> tuple[float, float]:
    """1組ずつ数えた（当たる確率の合計, 見積もりの払戻の合計）。"""
    values = _combo_values(legs)
    picked = [values[combo] for combo in formation.combos()]
    return sum(value[0] for value in picked), sum(value[1] for value in picked)


def test_上乗せの順と1着の確率の順に並べる() -> None:
    leg = _leg([0.5, 0.3, 0.2], [0.6, 0.2, 0.2])
    assert LegOrdering.BY_PROBABILITY.order(leg)[HORSE_NO].tolist() == [1, 2, 3]
    assert LegOrdering.BY_EDGE.order(leg)[HORSE_NO].tolist() == [2, 3, 1]
    assert LegOrdering.parse("上乗せ") is LegOrdering.BY_EDGE
    with pytest.raises(ValueError):
        LegOrdering.parse("人気")


def test_フォーメーションの点数は頭数のかけ算で_組を全部並べる() -> None:
    formation = Formation(((3, 7), (5,), (1, 2, 9), (4,), (6, 8)))
    assert formation.points == 12
    assert len(set(formation.combos())) == 12
    assert formation.contains((7, 5, 9, 4, 6))
    assert not formation.contains((7, 5, 3, 4, 6))
    assert formation.sizes_text() == "2×1×3×1×2"


def test_組の値は1組ずつ数えた値と同じ() -> None:
    legs = _legs()
    formation = Formation(((1, 3), (2,), (1, 2, 4), (2,), (2, 3)))
    choice = FormationValue(ESTIMATOR).of(formation, legs, POOL)
    hit, expected = _brute_payout(legs, formation)
    assert choice.hit_probability == pytest.approx(hit)
    assert choice.expected_payout == pytest.approx(expected)
    assert choice.expected_value == pytest.approx(expected / (12 * 100))


def test_全頭のフォーメーションの当たる確率は1() -> None:
    legs = _legs()
    formation = Formation(tuple(tuple(leg[HORSE_NO]) for leg in legs))
    assert FormationValue(ESTIMATOR).of(formation, legs, POOL).hit_probability == pytest.approx(1.0)


@pytest.mark.parametrize("ordering", list(LegOrdering))
@pytest.mark.parametrize("budget", [1, 7, 20, 60])
def test_探索は予算に収まる頭数の並びを全部試したいちばん良いものと同じ(ordering: LegOrdering, budget: int) -> None:
    legs = _legs()
    ordered = [ordering.order(leg) for leg in legs]
    values = _combo_values(legs)
    allowed = [sizes for sizes in itertools.product(*[range(1, len(leg) + 1) for leg in ordered]) if math.prod(sizes) <= budget]
    totals = {sizes: sum(values[combo][1] for combo in itertools.product(
        *[tuple(int(n) for n in leg[HORSE_NO].head(size)) for leg, size in zip(ordered, sizes, strict=True)])) for sizes in allowed}
    best_sizes = max(totals, key=lambda sizes: totals[sizes])
    best_payout = totals[best_sizes]
    choice = FormationSearch(ordering, FormationValue(ESTIMATOR)).best(legs, budget, POOL)
    assert choice.formation.sizes == best_sizes
    assert choice.formation.points <= budget
    assert choice.expected_payout == pytest.approx(best_payout)


def test_予算ごとの探索は1回の計算で全部の予算に答える() -> None:
    legs = _legs()
    search = FormationSearch(LegOrdering.BY_EDGE, FormationValue(ESTIMATOR))
    by_budget = search.best_by_budget(legs, [20, 50, 100], POOL)
    assert sorted(by_budget) == [20, 50, 100]
    assert all(choice.formation.points <= budget for budget, choice in by_budget.items())
    assert by_budget[20].expected_payout <= by_budget[50].expected_payout <= by_budget[100].expected_payout
    assert by_budget[50] == search.best(legs, 50, POOL)


def test_判断用の期待値が線未満なら見送り_以上なら本命の確率の積で多く少なくを分ける() -> None:
    judge = BudgetTierJudge()
    assert judge.judge(0.99, 1.0, 0.01, 0.0025) is DayDecision.SKIP
    assert judge.judge(1.0, 1.0, 0.0025, 0.0025) is DayDecision.BUY_LARGE
    assert judge.judge(1.0, 1.0, 0.0024, 0.0025) is DayDecision.BUY_SMALL
    assert DayDecision.BUY_LARGE.buys and DayDecision.BUY_SMALL.buys and not DayDecision.SKIP.buys
    assert [each.tier_label for each in DayDecision] == ["多く", "少なく", "見送り"]
    assert DayDecision.parse("買う（多く）") is DayDecision.BUY_LARGE
    assert DayDecision.buys_text("買う") and DayDecision.buys_text("買う（少なく）") and not DayDecision.buys_text("見送り")
    with pytest.raises(ValueError):
        DayDecision.parse("買う")


def test_本命の確率の積は各レースの最大のそろえた確率のかけ算() -> None:
    legs = [_leg([0.5, 0.3, 0.2], [0.6, 0.2, 0.2]), _leg([0.1, 0.6, 0.3], [0.3, 0.4, 0.3]), _leg([0.25, 0.25, 0.5], [0.3, 0.3, 0.4]),
            _leg([0.9, 0.1], [0.5, 0.5]), _leg([0.4, 0.4, 0.2], [0.4, 0.4, 0.2])]
    assert FavoriteProduct().of(legs) == pytest.approx(0.5 * 0.6 * 0.5 * 0.9 * 0.4)
    with pytest.raises(ValueError):
        FavoriteProduct().of([])


def test_段階の予算は判断で買う予算を決め_組む予算は重なりを除く() -> None:
    tiers = BudgetTiers(50, 30, 100, 0.0025)
    assert tiers.budgets == (30, 50, 100)
    assert tiers.budget_for(DayDecision.BUY_LARGE) == 100
    assert tiers.budget_for(DayDecision.BUY_SMALL) == 30
    assert tiers.budget_for(DayDecision.SKIP) == 30
    assert tiers.to_dict() == {"判断用の予算": 50, "少なく買う日の予算": 30, "多く買う日の予算": 100, "多く買う日の線": 0.0025}
    assert BudgetTiers(50, 50, 50, 0.0).budgets == (50,)
    with pytest.raises(ValueError):
        BudgetTiers(50, 100, 30, 0.0025)
    with pytest.raises(ValueError):
        BudgetTiers(0, 30, 100, 0.0025)


def test_材料の列の名前は式と同じ() -> None:
    assert (INVERSE_LOG, CARRY_LOG) == ("市場の組の確率の逆数の対数", "キャリーオーバーの比の対数")
