"""単勝オッズから見た確率（Harville の式）と、目的変数の基準（既存モデルの修正計画の 1・2）。"""

from __future__ import annotations

from dataclasses import replace
from itertools import permutations

import numpy as np
import pandas as pd
import pytest

from ..dataset import BaselineLogit, PLACE_HIT, TOP3, Top3Baseline, Top3TargetBuilder, TrainingData
from ..feature import PredictionTiming
from ..feature.odds import TOP2_RATE, TOP3_RATE, WIN_RATE, HarvillePlaces, MarketPlaces, MarketWinProbability


def _enumerated(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """1〜3着の並びを全部数えて出した、2着以内・3着以内の確率（Harville の式そのまま）。"""
    top2, top3 = np.zeros(len(p)), np.zeros(len(p))
    for first, second, third in permutations(range(len(p)), 3):
        chance = p[first] * p[second] / (1 - p[first]) * p[third] / (1 - p[first] - p[second])
        top2[[first, second]] += chance
        top3[[first, second, third]] += chance
    return top2, top3


def test_harville_places_match_enumeration():
    first_race = np.array([0.40, 0.25, 0.15, 0.12, 0.08])
    second_race = np.array([0.5, 0.3, 0.2])
    race_ids = pd.Series(["A"] * 5 + ["B"] * 3)
    places = HarvillePlaces().places(race_ids, pd.Series(np.r_[first_race, second_race]))
    for race, p in (("A", first_race), ("B", second_race)):
        top2, top3 = _enumerated(p)
        rows = places[race_ids == race]
        np.testing.assert_allclose(rows[TOP2_RATE], top2)
        np.testing.assert_allclose(rows[TOP3_RATE], top3)
        np.testing.assert_allclose(rows[WIN_RATE], p)


def test_harville_places_sum_to_the_number_of_places():
    rng = np.random.default_rng(3)
    p = rng.dirichlet(np.ones(16))
    places = HarvillePlaces().places(pd.Series(["R"] * 16), pd.Series(p))
    assert places[TOP2_RATE].sum() == pytest.approx(2.0)
    assert places[TOP3_RATE].sum() == pytest.approx(3.0)
    # 勝率が高い馬ほど、3着以内の確率も高い
    assert np.all(np.diff(places[TOP3_RATE].to_numpy()[np.argsort(p)]) > 0)


def test_market_win_probability_normalizes_within_races_and_skips_missing_odds():
    race_ids = pd.Series(["A", "A", "A", "B", "B"])
    odds = pd.Series([2.0, 4.0, np.nan, 3.0, 3.0])
    win = MarketWinProbability().of(race_ids, odds)
    np.testing.assert_allclose(win.to_numpy()[[0, 1]], [2 / 3, 1 / 3])
    assert np.isnan(win.iloc[2])
    np.testing.assert_allclose(win.to_numpy()[[3, 4]], [0.5, 0.5])


def test_top3_baseline_is_the_logit_of_the_market_top3_rate():
    entries = pd.DataFrame({"race_id": ["A"] * 4 + ["B"] * 3, "win_odds": [2.0, 3.5, 6.0, 12.0, np.nan, np.nan, np.nan]})
    baseline = Top3Baseline().build(entries)
    top3 = MarketPlaces().of(entries)[TOP3_RATE]
    np.testing.assert_allclose(baseline.to_numpy()[:4], np.log(top3[:4] / (1 - top3[:4])))
    # オッズの無いレースは、3 ÷ 頭数（3頭立てなら 1 → 端で丸める）
    assert (baseline.to_numpy()[4:] > 5).all()
    assert Top3Baseline().known_from is PredictionTiming.DAY_BEFORE


def test_baseline_is_used_only_from_the_day_before():
    baseline = BaselineLogit(pd.Series([0.1, -0.2]), PredictionTiming.DAY_BEFORE)
    assert baseline.for_timing(PredictionTiming.THURSDAY) is None
    assert baseline.for_timing(PredictionTiming.RACE_DAY) is baseline
    np.testing.assert_allclose(baseline.probabilities(), 1 / (1 + np.exp([-0.1, 0.2])))


def test_training_data_keeps_the_baseline_on_the_same_rows(training_data: TrainingData):
    values = pd.Series(np.arange(len(training_data), dtype=float), index=training_data.ids.index)
    data = replace(training_data, baseline=BaselineLogit(values, PredictionTiming.DAY_BEFORE))
    half = data.ids.index[: len(data) // 2]
    chosen = data.where(data.ids.index.isin(half))
    assert chosen.baseline.values.index.equals(chosen.ids.index)
    assert data.for_timing(PredictionTiming.THURSDAY).baseline is None
    assert data.for_timing(PredictionTiming.RACE_DAY).baseline is data.baseline


def test_place_hit_follows_the_payout_and_is_missing_when_place_is_not_sold():
    samples = pd.DataFrame({
        "finish": [1, 3, 3, 4, 2], "place_payout": [150, 0, 210, 0, 0], "field_size": [8, 7, 8, 8, 4],
    })
    targets = Top3TargetBuilder().build(samples)
    assert targets[TOP3].tolist() == [1, 1, 1, 0, 1]
    # 7頭立ての3着は複勝の払戻が無い（2着まで）。4頭立ては複勝を売らない
    assert targets[PLACE_HIT].tolist()[:4] == [1.0, 0.0, 1.0, 0.0] and np.isnan(targets[PLACE_HIT].iloc[4])
