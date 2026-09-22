"""まとまり J（人気と人気の履歴）の作り方（人気馬の設計書 09 の J）。

DB を使わず、手で作った記録を渡して確かめる。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from ..feature import BASE_FEATURES, POPULARITY_FEATURES, EntryRecords, FeatureCatalog, WorkoutCoverage
from ..feature.group import PopularityHistoryFeatures
from ..feature.history import AVERAGE_POPULARITY, WORSE_THAN_POPULARITY

RACE_DAY = date(2024, 6, 1)
PAST_RUN_COLUMNS = ["horse_id", "race_date", "race_id", "finish", "popularity"]
_EMPTY_COLUMNS = ["person_code", "race_date", "starts", "places"]


def _entry(horse_id: str, popularity: int | None = 2, *, prev_finish: int | None = None,
           prev_popularity: int | None = None) -> dict[str, Any]:
    """出走の行1行。まとまり J が読む列だけを入れる。"""
    return {
        "horse_id": horse_id, "race_date": pd.Timestamp(RACE_DAY), "popularity": popularity,
        "prev_finish": prev_finish, "prev_popularity": prev_popularity,
    }


def _run(days_before: int, finish: int | None, popularity: int | None,
         horse_id: str = "A") -> dict[str, Any]:
    """過去走1つ。"""
    return {
        "horse_id": horse_id, "race_date": pd.Timestamp(RACE_DAY - timedelta(days=days_before)),
        "race_id": f"r{days_before}", "finish": finish, "popularity": popularity,
    }


def _build(entries: list[dict[str, Any]], past_runs: list[dict[str, Any]] = ()) -> pd.DataFrame:
    records = EntryRecords(
        entries=pd.DataFrame(entries),
        past_runs=pd.DataFrame(list(past_runs), columns=PAST_RUN_COLUMNS),
        workouts=pd.DataFrame(), workout_coverage=WorkoutCoverage.complete(),
        jockey_days=pd.DataFrame(columns=_EMPTY_COLUMNS),
        trainer_days=pd.DataFrame(columns=_EMPTY_COLUMNS),
        sire_days=pd.DataFrame(), damsire_days=pd.DataFrame(),
    )
    return PopularityHistoryFeatures().build(records)


def test_the_four_features_are_numbers_in_group_j():
    assert [feature.name for feature in POPULARITY_FEATURES] == [
        "人気順位", "前走の人気と着順の差", WORSE_THAN_POPULARITY, AVERAGE_POPULARITY,
    ]
    assert all(feature.group == "J" and not feature.is_categorical for feature in POPULARITY_FEATURES)
    # A〜I に足しても名前が重ならない（人気を使う予想の一覧が作れる）
    assert len(FeatureCatalog(BASE_FEATURES + POPULARITY_FEATURES).names) == 75


def test_the_group_makes_exactly_the_four_features():
    features = _build([_entry("A", 1)])
    assert list(features.columns) == [feature.name for feature in POPULARITY_FEATURES]


def test_popularity_rank_comes_from_the_entry():
    features = _build([_entry("A", 1), _entry("B", 5)])
    assert features["人気順位"].tolist() == [1.0, 5.0]


def test_gap_is_the_previous_finish_minus_the_previous_popularity():
    entries = [
        _entry("A", prev_finish=3, prev_popularity=5),   # 人気より2つ良い着順
        _entry("B", prev_finish=8, prev_popularity=1),   # 人気より7つ悪い着順
        _entry("C", prev_finish=None, prev_popularity=1),
        _entry("D", prev_finish=2, prev_popularity=None),
    ]
    gaps = _build(entries)["前走の人気と着順の差"]
    assert gaps.tolist()[:2] == [-2.0, 7.0]
    assert np.isnan(gaps.iloc[2]) and np.isnan(gaps.iloc[3])


def test_recent_runs_count_the_five_runs_before_the_race_day():
    # 7走のうち、当日の1走（今回のレース自身）は使わず、その前の5走で数える
    runs = [
        _run(0, 1, 1),
        _run(14, 5, 2), _run(28, 1, 3), _run(42, 4, 4), _run(56, 2, 5), _run(70, 9, 6),
        _run(84, 1, 9),
    ]
    row = _build([_entry("A")], runs).iloc[0]
    # 14日前（5着 < 2番人気ではなく悪い）・42日前（4着と4番人気は同じで数えない）・70日前（9着 > 6番人気）
    assert row[WORSE_THAN_POPULARITY] == 2
    assert row[AVERAGE_POPULARITY] == pytest.approx((2 + 3 + 4 + 5 + 6) / 5)


def test_runs_without_a_finish_or_a_popularity_are_not_counted():
    runs = [_run(14, None, 2), _run(28, 6, None), _run(42, 8, 3)]
    row = _build([_entry("A")], runs).iloc[0]
    assert row[WORSE_THAN_POPULARITY] == 1 and row[AVERAGE_POPULARITY] == pytest.approx(3.0)


def test_a_horse_without_past_runs_has_missing_values():
    runs = [_run(14, 1, 1)]
    features = _build([_entry("A"), _entry("B")], runs)
    assert features.loc[0, AVERAGE_POPULARITY] == 1
    assert np.isnan(features.loc[1, AVERAGE_POPULARITY])
    assert np.isnan(features.loc[1, WORSE_THAN_POPULARITY])
