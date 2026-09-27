"""確率のずれ（確率の帯ごと）と、期待値の帯ごとの回収率（穴馬の設計書 16 の 5）。DB もモデルも使わず、手で作った値で確かめる。"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ..evaluation import ProbabilityBands, ValueBands
from ..evaluation.probability_bands import ACTUAL, BAND, COUNT, PREDICTED, RATIO
from ..evaluation.value_bands import ACTUAL_HIT, PAYBACK, PREDICTED_HIT, VALUE
from ..evaluation.value_bands import BAND as VALUE_BAND
from ..evaluation.value_bands import COUNT as POINTS


def test_probability_bands_compare_the_mean_prediction_with_the_actual_rate():
    # 0.05〜0.08 の帯に 4頭（予想 0.06、実際 1/4）、0.2〜0.25 の帯に 2頭（予想 0.22、実際 0/2）
    probability = pd.Series([0.06, 0.06, 0.06, 0.06, 0.22, 0.22])
    label = pd.Series([1, 0, 0, 0, 0, 0])
    rows = ProbabilityBands().table(label, probability)
    assert rows[BAND].tolist() == ["0.05〜0.08", "0.2〜0.25"]
    assert rows[COUNT].tolist() == [4, 2]
    np.testing.assert_allclose(rows[PREDICTED], [0.06, 0.22])
    np.testing.assert_allclose(rows[ACTUAL], [0.25, 0.0])
    np.testing.assert_allclose(rows[RATIO], [0.25 / 0.06, 0.0])


def test_probability_gap_is_the_count_weighted_mean_of_the_band_gaps():
    probability = pd.Series([0.06, 0.06, 0.06, 0.06, 0.22, 0.22])
    label = pd.Series([1, 0, 0, 0, 0, 0])
    expected = (4 * abs(0.06 - 0.25) + 2 * abs(0.22 - 0.0)) / 6
    assert ProbabilityBands().gap(label, probability) == pytest.approx(expected)
    # 確率が実際の割合とそろっていれば 0
    assert ProbabilityBands().gap(pd.Series([1, 0, 0, 0]), pd.Series([0.25] * 4)) == pytest.approx(0.0)


def test_value_bands_compare_the_expected_value_with_the_payback():
    # 期待値 0.7 の2点（外れ）、1.15 の2点（1点が 250円で当たり）、1.5 の1点（外れ）。払戻の欠損値は外れ
    value = pd.Series([0.7, 0.7, 1.15, 1.15, 1.5, np.nan])
    hit_probability = pd.Series([0.1, 0.1, 0.4, 0.4, 0.3, 0.2])
    payout = pd.Series([0, np.nan, 250, 0, 0, 500])
    rows = ValueBands().table(value, hit_probability, payout)
    assert rows[VALUE_BAND].tolist() == ["0.6〜0.8", "1.1〜1.2", "1.4以上"]
    assert rows[POINTS].tolist() == [2, 2, 1]
    np.testing.assert_allclose(rows[PREDICTED_HIT], [0.1, 0.4, 0.3])
    np.testing.assert_allclose(rows[ACTUAL_HIT], [0.0, 0.5, 0.0])
    np.testing.assert_allclose(rows[PAYBACK], [0.0, 1.25, 0.0])


def test_value_bands_sum_up_the_bets_above_a_line():
    value = pd.Series([0.7, 1.0, 1.15, np.nan])
    hit_probability = pd.Series([0.1, 0.4, 0.4, 0.2])
    payout = pd.Series([200, 300, 0, 500])
    bought = ValueBands().at_least(value, hit_probability, payout, 1.0)
    # 期待値の無い馬（4頭目）は数えない
    assert bought[POINTS] == 2 and bought[VALUE] == pytest.approx(1.075)
    assert bought[ACTUAL_HIT] == pytest.approx(0.5) and bought[PAYBACK] == pytest.approx(1.5)
    nothing = ValueBands().at_least(value, hit_probability, payout, 5.0)
    assert nothing[POINTS] == 0 and math.isnan(nothing[PAYBACK])
    # 期待値が1つも無い（木曜）なら、帯の表は空
    assert ValueBands().table(pd.Series([np.nan]), pd.Series([np.nan]), pd.Series([0])).empty
