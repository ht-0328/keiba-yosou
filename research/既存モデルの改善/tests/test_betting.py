"""買い方の部品（見込みの倍率・組み合わせの表・荒れ具合の計算・回収率の幅）。合成データだけを使う。印の買い方は test_marks.py。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.place_value import PlacePriceEstimator
from yosou.upset_level.dataset import BetType, UpsetLevel, UpsetLevelRule

from 既存モデルの改善.analysis.market import CombinationTable, RaceCombinations
from 既存モデルの改善.analysis.race_probability import FinishOrderProbability
from 既存モデルの改善.analysis.scores import BootstrapInterval, ThresholdChooser
from 既存モデルの改善.analysis.upset import UpsetClassCalculator


def test_place_price_estimator_learns_band_multipliers_and_round_trips():
    odds = pd.Series([1.2, 1.4, 2.5, 2.8, 12.0])
    payout = pd.Series([130.0, 0.0, 300.0, 330.0, 1500.0])
    estimator = PlacePriceEstimator().fit(odds, payout)
    estimate = estimator.estimate(pd.Series([1.3, 2.6, 12.0]))
    assert estimate.iloc[0] == pytest.approx(1.3 * 130 / 120)
    assert estimate.iloc[1] == pytest.approx(2.6 * np.mean([300 / 250, 330 / 280]))
    restored = PlacePriceEstimator.from_state(estimator.state())
    np.testing.assert_allclose(restored.estimate_array(np.array([1.3, 2.6])), estimate.to_numpy()[:2])


def test_combination_table_slices_races():
    frame = pd.DataFrame({"race_id": ["B", "A", "A"], "h1": [1, 2, 3], "h2": [2, 3, 1], "odds": [5.0, 7.0, 9.0],
                          "odds_high": [5.0, 7.0, 9.0]})
    table = CombinationTable(frame, width=2)
    assert len(table.race("A")) == 2 and len(table.race("B")) == 1 and len(table.race("Z")) == 0


def test_upset_levels_come_from_the_odds_of_each_combination():
    p = np.zeros(18)
    p[:3] = [0.6, 0.3, 0.1]
    # 単勝: 1番 2.0倍（固い）、2番 6.0倍（中荒れ）、3番 40倍（超荒れ）
    win = RaceCombinations(np.array([[1], [2], [3]]), np.array([2.0, 6.0, 40.0]), np.array([2.0, 6.0, 40.0]))
    levels = UpsetClassCalculator(UpsetLevelRule()).of_race(p, FinishOrderProbability(), {BetType.WIN: win})[BetType.WIN]
    np.testing.assert_allclose(levels, [0.6, 0.3, 0.0, 0.1])
    assert len(levels) == len(UpsetLevel)


def test_threshold_chooser_and_bootstrap_interval():
    value = pd.Series(np.r_[np.full(150, 1.05), np.full(150, 1.3)])
    payout = pd.Series(np.r_[np.full(150, 50.0), np.full(150, 150.0)])
    assert ThresholdChooser().choose(value, payout) == 1.1
    low, high = BootstrapInterval(rounds=200).of(pd.Series(np.arange(300) % 30), pd.Series(100.0, index=value.index), payout)
    assert low <= 1.0 <= high
