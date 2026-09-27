"""確率のずれを確かめる部品（Platt scaling・isotonic regression・較正の方法の比べ方・時点を替えた作り方）。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset.column_names import PLACE_PAYOUT, POPULARITY
from yosou.shared.feature import PredictionTiming
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE
from yosou.shared.workflow.calibration_check import LABEL, PART, PART_TEST, PART_VALID, PROBABILITY, SEGMENT, TIMING

from 既存モデルの改善.analysis.calibration import (
    RAW,
    WINDOW_COLUMN,
    CalibrationComparison,
    IsotonicCalibration,
    PlattCalibration,
)
from 既存モデルの改善.analysis.variants import variant_named

#: 実際の割合がいつも予想の半分になる、見積もりすぎの確率（検証とテストで同じずれ）。
_RNG = np.random.default_rng(0)


def _overconfident(rows: int) -> tuple[np.ndarray, np.ndarray]:
    probability = _RNG.uniform(0.05, 0.4, rows)
    label = (_RNG.uniform(0, 1, rows) < probability / 2).astype(int)
    return probability, label


def test_platt_and_isotonic_pull_an_overconfident_probability_back():
    probability, label = _overconfident(20_000)
    for calibration in (PlattCalibration(), IsotonicCalibration()):
        calibrated = calibration.fit(probability, label).apply(probability)
        # 見積もりすぎ（平均が実際の2倍）を、実際の割合の近くまで下げる
        assert calibrated.mean() == pytest.approx(label.mean(), abs=0.005)
        assert np.all(np.diff(calibrated[np.argsort(probability)]) >= -1e-9)  # 順は変えない


def test_calibrations_need_fitting_first():
    with pytest.raises(RuntimeError, match="fit"):
        PlattCalibration().apply(np.array([0.1]))
    with pytest.raises(RuntimeError, match="fit"):
        IsotonicCalibration().apply(np.array([0.1]))


def _frame() -> pd.DataFrame:
    """2つの区切り × 検証とテスト × 1000頭の、見積もりすぎの材料の表（期待値は確率 × 5）。"""
    parts = []
    for window, part in [("A", PART_VALID), ("A", PART_TEST), ("B", PART_VALID), ("B", PART_TEST)]:
        probability, label = _overconfident(1000)
        parts.append(pd.DataFrame({
            TIMING: "当日", PART: part, SEGMENT: "大穴", LABEL: label, PROBABILITY: probability,
            POPULARITY: _RNG.integers(7, 19, 1000), PLACE_PAYOUT: label * 500.0,
            PLACE_PROBABILITY: probability, PLACE_VALUE: probability * 5.0, WINDOW_COLUMN: window,
        }))
    return pd.concat(parts, ignore_index=True)


def test_comparison_calibrates_on_the_validation_period_and_scores_the_test_period():
    table = CalibrationComparison(_frame(), {"Platt scaling": PlattCalibration}).table()
    rows = {row[table.columns.index("方法")]: dict(zip(table.columns, row)) for row in table.rows}
    assert set(rows) == {RAW, "Platt scaling"}
    raw, platt = rows[RAW], rows["Platt scaling"]
    # テスト期間の行だけ（2つの区切り × 1000頭）を数える
    assert raw["頭数"] == 2000 and platt["頭数"] == 2000
    assert raw["実際 ÷ 予想"] == pytest.approx(0.5, abs=0.05) and platt["実際 ÷ 予想"] == pytest.approx(1.0, abs=0.1)
    assert platt["ログ損失"] < raw["ログ損失"] and platt["ログ損失が較正なしより小さい区切り"] == 2
    # 較正で確率が下がると、期待値1以上（確率 0.2 以上）の点数も減る
    assert platt["期待値1以上の点数"] < raw["期待値1以上の点数"]


def test_variant_at_another_timing_drops_the_columns_not_known_yet():
    improved = variant_named("longshots_in_top3", "improved")
    thursday = improved.at_timing(PredictionTiming.THURSDAY, available=improved.columns[:5])
    assert thursday.key == "improved-thursday" and thursday.timing is PredictionTiming.THURSDAY
    assert thursday.columns == improved.columns[:5] and thursday.segment_column == improved.segment_column
