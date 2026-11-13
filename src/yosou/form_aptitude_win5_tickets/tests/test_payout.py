"""配当の見積もり（発売票数の見積もり・材料・式・自分の1票と上限・式を作る行）のテスト。"""

from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 共通 import db

from ..payout import (
    CARRY_LOG,
    FEATURE_COLUMNS,
    INVERSE_LOG,
    PAYOUT_CEILING,
    ComboMarketProbability,
    PayoutCeiling,
    PayoutEstimator,
    PayoutFeatures,
    PayoutPool,
    PayoutTrainingRows,
    PoolSizeEstimate,
)
from ..repository import Win5HistoryRepository
from ..repository.win5_columns import RACE_DATE, SATURDAY, VOTES
from .win5_sample import FIRST_SUNDAY, FORECAST_DAY, NO_HIT_SUNDAY, PAYOUT_SLOPE, SATURDAY_VOTES, SUNDAY_VOTES


def _history(days: list[tuple[str, bool, int]]) -> pd.DataFrame:
    return pd.DataFrame([{RACE_DATE: day, SATURDAY: saturday, VOTES: votes} for day, saturday, votes in days])


def test_発売票数は同じ曜日の種類の直近10回の中央値で_その日より前だけを使う() -> None:
    sundays = [(f"2024-{month:02d}-{day:02d}", False, 1000 * index) for index, (month, day) in
               enumerate([(1, d) for d in (7, 14, 21, 28)] + [(2, d) for d in (4, 11, 18, 25)] + [(3, d) for d in (3, 10, 17, 24)], start=1)]
    history = _history([*sundays, ("2024-03-23", True, 500), ("2024-03-31", False, 999_999)])
    estimate = PoolSizeEstimate().of(history, date(2024, 3, 31), is_saturday=False)
    assert estimate == pytest.approx(np.median([1000 * index for index in range(3, 13)]))
    assert PoolSizeEstimate().of(history, date(2024, 3, 30), is_saturday=True) == 500


def test_同じ曜日の種類の回が無ければ曜日を問わず_前の回が無ければ止まる() -> None:
    history = _history([("2024-01-07", False, 3000), ("2024-01-14", False, 5000)])
    assert PoolSizeEstimate().of(history, date(2024, 1, 20), is_saturday=True) == 4000
    with pytest.raises(LookupError):
        PoolSizeEstimate().of(history, date(2024, 1, 7), is_saturday=False)


def test_材料は市場の組の確率の逆数の対数と_キャリーオーバーの比の対数() -> None:
    probability = 0.13 * 0.30 * 0.07 * 0.25 * 0.16
    features = PayoutFeatures().of(np.array([probability, 0.5]), 0.0, 1_000_000)
    assert features[INVERSE_LOG].iloc[0] == pytest.approx(math.log(1 / probability))
    assert features[INVERSE_LOG].iloc[0] == pytest.approx(9.1, abs=0.05)
    assert features[CARRY_LOG].tolist() == [0.0, 0.0]
    carried = PayoutFeatures().of(np.array([0.01]), 70_000_000, 1_000_000)
    assert carried[CARRY_LOG].iloc[0] == pytest.approx(math.log(2.0))


def test_式は過去の当たり組の傾きを当て直し_辞書にしても同じ値になる() -> None:
    rng = np.random.default_rng(0)
    inverse_log = rng.uniform(3, 14, 300)
    carry_log = rng.choice([0.0, 0.0, 0.0, 0.4], 300)
    log_payout = 4.0 + 0.95 * inverse_log + 0.9 * carry_log + rng.normal(0, 0.3, 300)
    features = pd.DataFrame({INVERSE_LOG: inverse_log, CARRY_LOG: carry_log})
    estimator = PayoutEstimator.fit(features, np.exp(log_payout))
    assert estimator.slopes[0] == pytest.approx(0.95, abs=0.02)
    assert estimator.intercept == pytest.approx(4.0, abs=0.2)
    assert estimator.smear == pytest.approx(math.exp(0.3 ** 2 / 2), abs=0.02)
    assert estimator.count == 300
    again = PayoutEstimator.from_dict(estimator.to_dict())
    assert again == estimator
    one = pd.DataFrame({INVERSE_LOG: [math.log(5000.0)], CARRY_LOG: [0.0]})
    assert again.estimate(one)[0] == pytest.approx(math.exp(estimator.intercept + estimator.slopes[0] * math.log(5000.0)) * estimator.smear)


def test_自分の1票で分け合い_払戻に回るお金と上限を超えない() -> None:
    money = 1_000_000_000.0
    ceiling = PayoutCeiling()
    popular, rare, huge = ceiling.apply(np.array([10_000.0, money, 1e15]), money)
    assert popular == pytest.approx(10_000.0, rel=1e-4)
    assert rare == pytest.approx(money / 2)
    assert huge == PAYOUT_CEILING
    small_pool = PayoutCeiling().apply(np.array([1e12]), 50_000_000.0)[0]
    assert small_pool < 50_000_000.0


def test_払戻に回るお金は売上の7割とキャリーオーバー() -> None:
    pool = PayoutPool(votes=1_000_000, carry=30_000_000)
    assert pool.sales_share == pytest.approx(70_000_000)
    assert pool.money == pytest.approx(100_000_000)


def test_当たり組の市場の組の確率は5頭のオッズから見た勝率のかけ算() -> None:
    odds = pd.Series([[2.0, 4.0, 2.0, 2.0, 2.0], [2.0, None, 2.0, 2.0, 2.0]])
    sums = pd.Series([[1.0, 1.0, 1.0, 1.0, 1.0], [1.0, 1.0, 1.0, 1.0, 1.0]])
    probability = ComboMarketProbability().of_winners(odds, sums)
    assert probability.iloc[0] == pytest.approx(0.5 ** 4 * 0.25)
    assert math.isnan(probability.iloc[1])


def test_式を作る行は的中無と_前の回の無い回を除き_発売票数は前の回から見積もる(win5_db: Path) -> None:
    with db.open_db(win5_db) as con:
        history = Win5HistoryRepository(con).read(FORECAST_DAY)
    rows = PayoutTrainingRows().of(history)
    first_day = history[RACE_DATE].min()
    no_hit_day = (FIRST_SUNDAY + timedelta(weeks=NO_HIT_SUNDAY)).isoformat()
    assert first_day not in set(rows[RACE_DATE])
    assert no_hit_day not in set(rows[RACE_DATE])
    assert len(rows) == history[RACE_DATE].nunique() - 2
    assert list(rows.columns) == [RACE_DATE, *FEATURE_COLUMNS, "払戻"]
    assert set(rows[CARRY_LOG]) == {0.0}
    assert SATURDAY_VOTES < SUNDAY_VOTES


def test_架空の過去のWIN5で作った式は_払戻を作った傾きに近い(estimator: PayoutEstimator) -> None:
    assert estimator.slopes[0] == pytest.approx(PAYOUT_SLOPE, abs=0.25)
