"""評価指標の計算（穴馬の設計書 16）。DB もモデルも使わず、手で作った小さな学習データで確かめる。"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ..dataset import RACE_ID, TrainingData
from ..dataset.column_names import PLACE_PAYOUT, POPULARITY
from ..evaluation.metric_calculator import MetricCalculator
from ..feature import BASE_FEATURES, FeatureCatalog

LABEL = "3着以内"


def _data(races: list[str], popularity: list[float], label: list[int], payout: list[float]) -> TrainingData:
    """1行 = 1頭の、評価に要る列だけを持つ学習データ。"""
    index = pd.RangeIndex(len(races))
    return TrainingData(
        ids=pd.DataFrame({RACE_ID: races}, index=index),
        features=pd.DataFrame(index=index),
        targets=pd.DataFrame({LABEL: label}, index=index),
        evaluation=pd.DataFrame({POPULARITY: popularity, PLACE_PAYOUT: payout}, index=index),
        catalog=FeatureCatalog(BASE_FEATURES),
        label_name=LABEL,
    )


#: 2レース × 3頭。レース A は 4番人気（確率1位）が 3着以内、レース B は 5番人気（確率1位）が 3着以内。
RACES = ["A", "A", "A", "B", "B", "B"]
POPULARITY_RANKS = [4, 5, 6, 4, 5, 6]
LABELS = [1, 0, 0, 0, 1, 0]
PAYOUTS = [250, 0, 0, 0, 400, 0]
PROBABILITY = np.array([0.3, 0.2, 0.1, 0.1, 0.4, 0.2])


def _calculator() -> MetricCalculator:
    return MetricCalculator(_data(RACES, POPULARITY_RANKS, LABELS, PAYOUTS))


def test_top_pick_rate_and_payback_follow_the_highest_probability():
    calculator = _calculator()
    assert calculator.top_pick_place_rate(PROBABILITY) == 1.0
    # 払戻 250 + 400 を、100円 × 2レースで割る
    assert calculator.top_pick_place_payback(PROBABILITY) == pytest.approx(6.5 / 2)


def test_popularity_pick_is_the_most_popular_runner_of_each_race():
    calculator = _calculator()
    # どちらのレースも 4番人気が基準。A は 3着以内（払戻 250）、B は馬券外
    assert calculator.popularity_pick_place_rate() == 0.5
    assert calculator.popularity_pick_place_payback() == pytest.approx(250 / 200)


def test_popularity_pick_skips_runners_without_popularity():
    data = _data(["A", "A"], [float("nan"), 7], [1, 0], [300, 0])
    assert MetricCalculator(data).popularity_pick_place_rate() == 0.0


def test_auc_within_popularity_compares_only_runners_of_the_same_popularity():
    calculator = _calculator()
    # 4番人気どうし（A が 1、B が 0）も 5番人気どうしも、確率の高いほうが 1 なので 1.0。6番人気は 0 だけなので数えない
    assert calculator.auc_within_popularity(PROBABILITY) == 1.0
    reversed_probability = np.array([0.1, 0.4, 0.1, 0.3, 0.2, 0.2])
    assert calculator.auc_within_popularity(reversed_probability) == 0.0


def test_auc_within_popularity_is_nan_when_no_popularity_has_both_labels():
    data = _data(["A", "A", "B", "B"], [4, 5, 4, 5], [1, 0, 1, 0], [200, 0, 200, 0])
    assert math.isnan(MetricCalculator(data).auc_within_popularity(np.array([0.3, 0.2, 0.3, 0.2])))


def test_general_metrics_are_still_available():
    calculator = _calculator()
    assert calculator.auc(PROBABILITY) == 1.0
    assert 0.0 < calculator.log_loss(PROBABILITY) and 0.0 < calculator.brier(PROBABILITY) < 1.0
