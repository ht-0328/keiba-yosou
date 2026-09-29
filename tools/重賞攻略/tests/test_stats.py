"""切り口ごとの成績と検定の計算。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from 重賞攻略 import stats  # noqa: E402


def _rows(finishes: list[float | None], win_payout: float = 0.0, place_payout: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame({
        "finish": finishes,
        "win_payout": [win_payout] * len(finishes),
        "place_payout": [place_payout] * len(finishes),
    })


def test_perf_counts_missing_finish_as_out():
    """競走中止・失格（着順なし）は「出走して馬券外」。"""
    perf = stats.perf_of(_rows([1, 2, 3, 4, None]))
    assert perf["runs"] == 5
    assert perf["finish_counts"] == "1-1-1-2"
    assert perf["place_pct"] == pytest.approx(60.0)
    assert perf["out_pct"] == pytest.approx(40.0)


def test_binomial_p_is_small_only_for_real_deviations():
    """基準どおりなら p は大きく、大きくずれるほど小さい。"""
    assert stats.binomial_p(8, 16, 0.5) > 0.9
    assert stats.binomial_p(15, 16, 0.5) < 0.01
    assert stats.binomial_p(1, 16, 0.5) < 0.01


def test_two_proportion_p_handles_empty_groups():
    assert stats.two_proportion_p(0, 0, 5, 10) == 1.0
    assert stats.two_proportion_p(9, 10, 1, 10) < 0.01


def test_against_rest_compares_with_the_other_horses():
    band = stats.against_rest("4歳", _rows([1, 2, 1, 2]), _rows([9, 9, 9, 9]))
    assert band.diff_pt == pytest.approx(100.0)
    assert band.p_value < 0.05
    assert stats.mark(band.p_value) == "◎"


def test_against_base_without_base_skips_the_test():
    band = stats.against_base("前", _rows([1, 4]), None)
    assert band.base_place_pct is None and band.p_value is None
    assert stats.mark(band.p_value) == "―"
