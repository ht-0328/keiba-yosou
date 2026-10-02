"""1着の確率から 2着・3着の確率を出す計算（設計書 03 の 5・10 の 10.）を確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..ml_model import OrderLambdaFitter, OrderProbability

#: 架空の6頭立ての1着の確率（合計 1）。
_WIN = np.array([0.40, 0.25, 0.15, 0.10, 0.06, 0.04])


def test_trifecta_sums_to_one_and_places_sum_to_counts() -> None:
    order = OrderProbability()
    orders, probability = order.trifecta(_WIN, 0.8)
    assert len(orders) == 6 * 5 * 4
    assert np.isclose(probability.sum(), 1.0)
    places = order.places(_WIN, 0.8)
    assert np.allclose(places[:, 0], _WIN)
    assert np.isclose(places[:, 1].sum(), 2.0)
    assert np.isclose(places[:, 2].sum(), 3.0)


def test_lower_lambda_spreads_places_to_weaker_horses() -> None:
    order = OrderProbability()
    harville, spread = order.places(_WIN, 1.0), order.places(_WIN, 0.8)
    assert spread[0, 2] < harville[0, 2]
    assert spread[-1, 2] > harville[-1, 2]


def test_lambda_fitter_finds_the_lambda_that_made_the_results() -> None:
    rng = np.random.default_rng(0)
    rows = []
    for race in range(3000):
        order = OrderProbability().trifecta(_WIN, 0.7)
        pick = rng.choice(len(order[1]), p=order[1] / order[1].sum())
        first, second, third = order[0][pick]
        finish = np.full(len(_WIN), 9)
        finish[[first, second, third]] = [1, 2, 3]
        rows.append(pd.DataFrame({"race": race, "p": _WIN, "finish": finish}))
    table = pd.concat(rows, ignore_index=True)
    fitted = OrderLambdaFitter().fit(table["p"].to_numpy(), table["race"].to_numpy(), table["finish"].to_numpy())
    assert abs(fitted - 0.7) <= 0.1
