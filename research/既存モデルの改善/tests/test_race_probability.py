"""着順の並びの確率・Stern の補正の推定・レースの中の勝率の学習（合成データだけ）。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import RACE_ID
from yosou.shared.dataset.column_names import FINISH
from yosou.shared.feature.odds import TOP3_RATE, WIN_RATE, HarvillePlaces

from 既存モデルの改善.analysis.combined import RaceProbabilityBuilder, StrengthFeatures
from 既存モデルの改善.analysis.race_probability import (
    FinishOrderProbability,
    RaceFinishes,
    RaceStrengthModel,
    SternExponentFitter,
)

P = np.array([0.40, 0.25, 0.15, 0.12, 0.08])


def test_harville_without_correction_matches_the_market_top3_rate():
    order = FinishOrderProbability(1.0, 1.0)
    expected = HarvillePlaces().places(pd.Series(["R"] * len(P)), pd.Series(P))[TOP3_RATE].to_numpy()
    np.testing.assert_allclose(order.top_three(P), expected)


def test_order_tables_add_up():
    order = FinishOrderProbability(0.85, 0.75)
    triple = order.ordered_triple(P)
    assert triple.sum() == pytest.approx(1.0)
    np.testing.assert_allclose(triple.sum(axis=(1, 2)), P)
    assert order.ordered_pair(P).sum() == pytest.approx(1.0)
    assert order.quinella(P).sum() == pytest.approx(2.0)
    assert order.top_three(P).sum() == pytest.approx(3.0)
    trio = order.trio(P)
    assert trio[0, 1, 2] == pytest.approx(trio[2, 0, 1])
    # 補正で2着・3着の人気馬の寄りが弱まり、いちばん人気薄の3着以内率が Harville より上がる
    assert order.top_three(P)[-1] > FinishOrderProbability().top_three(P)[-1]


def _simulated_races(count: int, lam: float, mu: float, seed: int) -> list[tuple[np.ndarray, int, int, int]]:
    rng = np.random.default_rng(seed)
    races = []
    for _ in range(count):
        p = rng.dirichlet(np.ones(10) * 0.8)
        order = FinishOrderProbability(lam, mu).ordered_triple(p).ravel()
        first, second, third = np.unravel_index(rng.choice(len(order), p=order / order.sum()), (10, 10, 10))
        races.append((p, int(first), int(second), int(third)))
    return races


def test_stern_fitter_recovers_the_exponents():
    lam, mu = SternExponentFitter().fit(_simulated_races(3000, 0.8, 0.65, seed=1))
    assert lam == pytest.approx(0.8, abs=0.08) and mu == pytest.approx(0.65, abs=0.08)


def test_race_finishes_skip_races_without_a_single_winner():
    table = pd.DataFrame({"race": ["A"] * 3 + ["B"] * 3, "p": [0.5, 0.3, 0.2] * 2, "finish": [1, 2, 3, 1, 1, 3]})
    races = RaceFinishes().build(table["race"], table["p"], table["finish"])
    assert len(races) == 1 and races[0][1:] == (0, 1, 2)


def test_race_strength_model_recovers_the_weights():
    rng = np.random.default_rng(5)
    rows = []
    for race in range(4000):
        market = rng.dirichlet(np.ones(12))
        shift = rng.normal(0, 0.5, 12)
        score = 1.1 * np.log(market) + 0.6 * shift
        win = np.exp(score) / np.exp(score).sum()
        winner = rng.choice(12, p=win)
        rows.append(pd.DataFrame({"race": race, "log_market": np.log(market), "shift": shift, "won": np.arange(12) == winner}))
    table = pd.concat(rows, ignore_index=True)
    model = RaceStrengthModel().fit(table[["log_market", "shift"]].to_numpy(), table["race"], table["won"].to_numpy(float))
    assert model.weights[0] == pytest.approx(1.1, abs=0.1) and model.weights[1] == pytest.approx(0.6, abs=0.1)
    probability = model.predict(table[["log_market", "shift"]].to_numpy(), table["race"])
    np.testing.assert_allclose(pd.Series(probability).groupby(table["race"]).sum(), 1.0)


def test_race_strength_model_rejects_missing_values():
    features = np.array([[np.log(0.6)], [np.log(0.4)]])
    with pytest.raises(ValueError):
        RaceStrengthModel().fit(features, pd.Series(["A", "A"]), np.array([1.0, np.nan]))


def test_race_probability_builder_learns_even_when_some_finishes_are_missing():
    """着順の無い馬（取消など）がいても、1着でない馬として扱い、重みを学ぶ（出発点の 1 のまま止まらない）。"""
    rng = np.random.default_rng(7)
    rows = []
    for race in range(1500):
        market = rng.dirichlet(np.ones(10))
        win = market ** 1.3 / (market ** 1.3).sum()
        order = rng.choice(10, size=10, replace=False, p=win)
        finish = pd.array(np.argsort(order) + 1, dtype="Int32")
        finish[9] = pd.NA if race % 3 == 0 else finish[9]
        rows.append(pd.DataFrame({RACE_ID: f"R{race}", WIN_RATE: market, FINISH: finish}))
    valid = pd.concat(rows, ignore_index=True)
    fit = RaceProbabilityBuilder(StrengthFeatures(())).fit(valid)
    assert fit.model.weights[0] == pytest.approx(1.3, abs=0.15)
