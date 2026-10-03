"""1着のモデル用に持ち替える ``WinTargetData`` のテスト（設計書 10・15 の 14）。合成DB の学習データを使う。"""

from __future__ import annotations

import numpy as np

from yosou.shared.dataset import WIN, TrainingData
from yosou.shared.dataset.column_names import WIN_ODDS
from yosou.shared.feature import PredictionTiming

from ..dataset import WinTargetData


def test_training_data_switches_the_label_and_the_baseline(training_data: TrainingData) -> None:
    win = WinTargetData().training(training_data)
    assert win.label_name == WIN and win.label.isin([0, 1]).all()
    assert len(win) == len(training_data) and win.features.shape == training_data.features.shape
    # 基準はオッズから見た勝率（レースで合計 1）。3着以内の基準（合計 3）とは別
    probabilities = win.baseline.probabilities().groupby(win.ids["レースID"]).sum()
    assert np.allclose(probabilities, 1.0, atol=1e-6)
    assert win.baseline.known_from is PredictionTiming.DAY_BEFORE
    # オッズの高い馬ほど基準は低い
    odds = win.evaluation[WIN_ODDS]
    assert win.baseline.probabilities()[odds.idxmin()] > win.baseline.probabilities()[odds.idxmax()]


def test_thursday_has_no_baseline(training_data: TrainingData) -> None:
    thursday = WinTargetData().training(training_data).for_timing(PredictionTiming.THURSDAY)
    assert thursday.baseline is None
    assert WinTargetData().training(training_data).for_timing(PredictionTiming.DAY_BEFORE).baseline is not None
