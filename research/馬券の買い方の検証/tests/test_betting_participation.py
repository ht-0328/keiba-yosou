"""契約: 参加パターンは、荒れ判定・自信判定・週の上位・重賞から、買うレースと広め/少点数の別を決める。"""

import numpy as np
import pandas as pd
import pytest

from yosou.upset_level.dataset import BetType

from 馬券の買い方の検証.analysis import column_names as names
from 馬券の買い方の検証.analysis.participation import (
    PATTERNS,
    AllRacesPattern,
    ConfidenceJudge,
    ConfidentRacesPattern,
    UnionPattern,
    UpsetJudge,
    UpsetRacesPattern,
    WeeklyMode,
    WeeklyTopPattern,
    WeeklyWithGradedPattern,
    pattern_by_key,
)
from 馬券の買い方の検証.analysis.ticket import Breadth


def _races():
    """2週 × 4レース。荒れ度は r1 が最大、自信は r4 の本命が最高だが危険、r3 は本命が人気馬でない。"""
    return pd.DataFrame({
        names.RACE_ID: [f"r{i}" for i in range(1, 9)],
        names.WEEK: ["2025-07-05"] * 4 + ["2025-07-12"] * 4,
        names.IS_GRADED: [False, False, False, True, False, True, False, False],
        names.upset_column(BetType.TRIO): [0.9, 0.7, 0.3, 0.1, 0.8, 0.2, 0.6, np.nan],
        names.upset_column(BetType.WIN): [0.5] * 8,
        names.FAVORITE_PROB: [0.4, 0.55, 0.6, 0.7, 0.5, 0.65, 0.45, 0.52],
        names.FAVORITE_DANGER: [0.3, 0.3, np.nan, 0.7, 0.2, 0.35, 0.5, 0.1],
    })


def _ids(participation, wide=True):
    return participation.wide_ids if wide else participation.narrow_ids


def test_judges():
    races = _races()
    assert list(UpsetJudge(0.6).is_upset(races, BetType.TRIO)) == [True, True, False, False, True, False, True, False]
    assert not UpsetJudge(None).is_upset(races, BetType.TRIO).any()
    judge = ConfidenceJudge(0.5, 0.4)
    assert list(judge.is_confident(races)) == [False, True, False, False, True, True, False, True]
    assert list(ConfidenceJudge(0.5, 0.4, unknown_danger_is_confident=True).is_confident(races)) == [False, True, True, False, True, True, False, True]
    assert judge.scores(races).isna().tolist() == [False, False, True, True, False, False, True, False]
    assert not ConfidenceJudge(None, 0.4).is_confident(races).any()


def test_basic_patterns():
    races, upset, confidence = _races(), UpsetJudge(0.6), ConfidenceJudge(0.5, 0.4)
    everyone = AllRacesPattern().select(races, upset, confidence, BetType.TRIO, None)
    assert everyone.wide_ids == ["r1", "r2", "r5", "r7"] and everyone.narrow_ids == ["r3", "r4", "r6", "r8"]
    assert everyone.race_count == 8 and everyone.selected_count == 8
    fixed = AllRacesPattern(Breadth.NARROW).select(races, upset, confidence, BetType.TRIO, None)
    assert fixed.wide_ids == [] and len(fixed.narrow_ids) == 8
    assert UpsetRacesPattern().select(races, upset, confidence, BetType.TRIO, None).wide_ids == ["r1", "r2", "r5", "r7"]
    assert ConfidentRacesPattern().select(races, upset, confidence, BetType.TRIO, None).narrow_ids == ["r2", "r5", "r6", "r8"]
    union = UnionPattern().select(races, upset, confidence, BetType.TRIO, None)
    assert union.wide_ids == ["r1", "r2", "r5", "r7"] and union.narrow_ids == ["r2", "r5", "r6", "r8"] and union.selected_count == 6


def test_weekly_patterns_pick_top_k_per_week():
    races, upset, confidence = _races(), UpsetJudge(None), ConfidenceJudge(None, 0.4)
    weekly = WeeklyTopPattern(WeeklyMode.UPSET).select(races, upset, confidence, BetType.TRIO, 2)
    assert weekly.wide_ids == ["r1", "r2", "r5", "r7"] and weekly.narrow_ids == []
    weekly_conf = WeeklyTopPattern(WeeklyMode.CONFIDENT).select(races, upset, confidence, BetType.TRIO, 1)
    assert weekly_conf.narrow_ids == ["r2", "r6"]  # r4 は危険、r3 は人気馬でないので点が無い
    both = WeeklyTopPattern(WeeklyMode.BOTH).select(races, upset, confidence, BetType.TRIO, 1)
    assert both.wide_ids == ["r1", "r5"] and both.narrow_ids == ["r2", "r6"]
    with pytest.raises(ValueError):
        WeeklyTopPattern(WeeklyMode.UPSET).select(races, upset, confidence, BetType.TRIO, None)


def test_weekly_with_graded_adds_graded_races():
    races = _races()
    pattern = WeeklyWithGradedPattern(WeeklyTopPattern(WeeklyMode.UPSET))
    selected = pattern.select(races, UpsetJudge(0.6), ConfidenceJudge(None, 0.4), BetType.TRIO, 1)
    assert selected.wide_ids == ["r1", "r5"] and selected.narrow_ids == ["r4", "r6"]  # 重賞 r4・r6 は荒れないので少点数
    assert pattern.needs.upset and pattern.needs.top_k and pattern.needs.wide and pattern.needs.narrow and not pattern.needs.form


def test_pattern_catalog():
    assert len(PATTERNS) == 12 and pattern_by_key("04union").label.startswith("④")
    with pytest.raises(LookupError):
        pattern_by_key("no-such")
