"""特徴量の作り方（設計書 09）と、開催日より前のものだけを使う決まり（設計書 11 の 2）。

DB を使わず、手で作った記録を渡して確かめる。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
import pytest

from ..feature import (
    CATEGORICAL_FEATURES,
    FEATURE_NAMES,
    EntryRecords,
    FeatureBuilder,
    PredictionTiming,
)
from ..feature.group.workout_features import NO_WORKOUT

RACE_DAY = date(2024, 6, 1)
OTHER_RACE = "2024060105010102"


def _entry(horse_id: str, **values: Any) -> dict[str, Any]:
    """出走の記録1行。書かない列は、ありふれた値か欠損値。"""
    row: dict[str, Any] = {
        "race_id": "2024060105010101", "race_date": pd.Timestamp(RACE_DAY), "month": 6,
        "venue": "東京", "surface": "芝", "course": "芝・左", "distance_m": 1600, "condition": "良",
        "class_order": 3, "field_size": 3, "mixed_sex": True,
        "horse_id": horse_id, "sex": "牡", "age": 4, "affiliation": "美浦", "frame_no": 1, "horse_no": 1,
        "carried": 57.0, "body_weight": 480, "weight_change": 2, "blinker": "なし",
        "jockey_code": "00001", "apprentice": "減量なし", "jockey_change": "継続", "trainer_code": "00001",
        "prev_finish": None, "prev_time_diff": None, "prev_popularity": None, "prev_last3f": None,
        "prev_last3f_rank": None, "prev_corner4": None, "prev_field_size": None, "interval_days": None,
        "distance_change": "前走なし", "surface_change": "前走なし", "class_change": "前走なし", "venue_change": "前走なし",
        "style_before": None, "ck_total_runs": 0, "ck_total_wins": 0, "ck_total_places": 0,
        "ck_venue_runs": 0, "ck_venue_places": 0, "ck_band_runs": 0, "ck_band_places": 0,
        "ck_going_runs": 0, "ck_going_places": 0, "course_runs_before": 0, "course_places_before": 0,
        "best_time_unit_rank": None, "best_time_dist_rank": None, "lead_candidates": 0,
        "sire": "父A", "grandsire": "父父A", "damsire": "母父A",
    }
    row.update(values)
    return row


PAST_RUN_COLUMNS = [
    "horse_id", "race_date", "race_id", "finish", "time_diff", "last3f_rank", "corner4", "field_size",
]
WORKOUT_COLUMNS = ["horse_id", "work_date", "work_time", "course", "four_furlongs", "last_furlong"]
PEOPLE_DAY_COLUMNS = ["person_code", "race_date", "starts", "places"]
PEDIGREE_DAY_COLUMNS = ["pedigree_name", "surface", "race_date", "starts", "places"]


def _records(entries: list[dict[str, Any]], *, past_runs: list[dict[str, Any]] = (),
             workouts: list[dict[str, Any]] = (), jockey_days: list[dict[str, Any]] = (),
             sire_days: list[dict[str, Any]] = ()) -> EntryRecords:
    return EntryRecords(
        entries=pd.DataFrame(entries),
        past_runs=pd.DataFrame(list(past_runs), columns=PAST_RUN_COLUMNS),
        workouts=pd.DataFrame(list(workouts), columns=WORKOUT_COLUMNS),
        jockey_days=pd.DataFrame(list(jockey_days), columns=PEOPLE_DAY_COLUMNS),
        trainer_days=pd.DataFrame(columns=PEOPLE_DAY_COLUMNS),
        sire_days=pd.DataFrame(list(sire_days), columns=PEDIGREE_DAY_COLUMNS),
        damsire_days=pd.DataFrame(columns=PEDIGREE_DAY_COLUMNS),
    )


def _pedigree_day(name: str, surface: str, days_before: int, starts: int, places: int) -> dict[str, Any]:
    """血統の産駒の、1日ぶんの成績。"""
    return {"pedigree_name": name, "surface": surface, "race_date": _day(days_before),
            "starts": starts, "places": places}


def test_pedigree_rates_count_the_progeny_of_the_last_365_days():
    days = [
        _pedigree_day("父A", "芝", 400, 100, 100),   # 365日より前: 入れない
        _pedigree_day("父A", "芝", 200, 10, 4),      # 芝で 10走4回
        _pedigree_day("父A", "ダート", 100, 10, 1),  # ダートで 10走1回
        _pedigree_day("父A", "芝", 0, 5, 5),         # 当日: 入れない
    ]
    features = _build(_records([_entry("A"), _entry("B", horse_no=2, sire="父Z")], sire_days=days))
    # 芝ダを問わない力は 20走5回、同じ芝ダ（芝）だけなら 10走4回
    assert features.loc[0, "父の産駒の近1年の3着以内の割合"] == pytest.approx(5 / 20)
    assert features.loc[0, "父の産駒の同じ芝ダでの近1年の3着以内の割合"] == pytest.approx(4 / 10)
    # 産駒の記録が無い父は欠損値
    assert np.isnan(features.loc[1, "父の産駒の近1年の3着以内の割合"])


def _day(days_before: int) -> pd.Timestamp:
    return pd.Timestamp(RACE_DAY - timedelta(days=days_before))


def _run(days_before: int, finish: int | None, time_diff: float = 0.5) -> dict[str, Any]:
    """馬A の過去走1つ。8頭立てで、4コーナーは4番手。"""
    return {
        "horse_id": "A", "race_date": _day(days_before), "race_id": f"r{days_before}",
        "finish": finish, "time_diff": time_diff, "last3f_rank": finish, "corner4": 4, "field_size": 8,
    }


def _workout(horse_id: str, days_before: int, time: str, course: str,
             four_furlongs: float, last_furlong: float) -> dict[str, Any]:
    """調教1本。``time`` は調教時刻（``"0600"``）。"""
    return {
        "horse_id": horse_id, "work_date": _day(days_before), "work_time": time, "course": course,
        "four_furlongs": four_furlongs, "last_furlong": last_furlong,
    }


def _build(records: EntryRecords, timing: PredictionTiming = PredictionTiming.RACE_DAY) -> pd.DataFrame:
    return FeatureBuilder().build(records, timing)


def test_recent_form_uses_five_runs_before_the_race_day():
    # 7走のうち、当日の1走（今回のレース自身）は使わず、その前の5走（1〜5着）だけで数える
    runs = [
        _run(0, 9),
        _run(14, 1), _run(28, 2), _run(42, 3), _run(56, 4), _run(70, 5),
        _run(84, 12),
    ]
    features = _build(_records([_entry("A")], past_runs=runs))
    row = features.iloc[0]
    assert row["近5走の数"] == 5
    assert row["近5走の平均着順"] == pytest.approx(3.0)
    assert row["近5走の最高着順"] == 1
    assert row["近5走の平均4コーナー位置"] == pytest.approx(0.5)


def test_recent_form_skips_missing_finish_and_counts_debut_as_zero():
    runs = [_run(14, None), _run(28, 4)]
    features = _build(_records([_entry("A"), _entry("B", horse_no=2)], past_runs=runs))
    assert features.loc[0, "近5走の数"] == 2 and features.loc[0, "近5走の平均着順"] == 4
    assert features.loc[1, "近5走の数"] == 0 and np.isnan(features.loc[1, "近5走の平均着順"])


def test_jockey_rate_counts_365_days_until_the_day_before():
    days = [
        {"person_code": "00001", "race_date": _day(400), "starts": 10, "places": 10},  # 365日より前: 入れない
        {"person_code": "00001", "race_date": _day(365), "starts": 4, "places": 1},    # ちょうど 365日前: 入れる
        {"person_code": "00001", "race_date": _day(1), "starts": 6, "places": 2},      # 前日: 入れる
        {"person_code": "00001", "race_date": _day(0), "starts": 5, "places": 5},      # 当日: 入れない
    ]
    features = _build(_records([_entry("A"), _entry("B", horse_no=2, jockey_code="00009")], jockey_days=days))
    assert features.loc[0, "騎手の近1年の3着以内の割合"] == pytest.approx(3 / 10)
    assert np.isnan(features.loc[1, "騎手の近1年の3着以内の割合"])


def test_workouts_use_14_days_before_the_race_day():
    sessions = [
        _workout("A", 15, "0600", "坂路", 50.0, 11.0),    # 15日前: 入れない
        _workout("A", 14, "0600", "ウッド", 53.0, 12.0),  # ちょうど 14日前: 入れる
        _workout("A", 3, "0600", "坂路", 52.0, 12.4),
        _workout("A", 3, "0700", "坂路", 51.5, 12.1),     # 同じ日なら、時刻の遅い方が直近
        _workout("A", 0, "0600", "ウッド", 49.0, 11.0),   # 当日: 入れない
        _workout("B", 20, "0600", "坂路", 52.0, 12.0),    # 14日より前しか無い馬
    ]
    features = _build(_records([_entry("A"), _entry("B", horse_no=2)], workouts=sessions))
    horse_a, horse_b = features.iloc[0], features.iloc[1]
    assert horse_a["14日以内の調教の本数"] == 3
    assert horse_a["直近の調教のコース"] == "坂路"
    assert horse_a["坂路の直近の4ハロンタイム"] == 51.5 and horse_a["坂路の直近のラスト1ハロン"] == 12.1
    assert horse_a["ウッドの直近の4ハロンタイム"] == 53.0
    assert horse_b["14日以内の調教の本数"] == 0 and horse_b["直近の調教のコース"] == NO_WORKOUT
    assert np.isnan(horse_b["坂路の直近の4ハロンタイム"])


def test_field_comparison_ranks_within_the_same_race():
    runs = [{**_run(14, 1, time_diff=0.3), "horse_id": "A"}, {**_run(14, 2, time_diff=0.3), "horse_id": "B"},
            {**_run(14, 3, time_diff=1.0), "horse_id": "C"}]
    entries = [
        _entry("A", carried=55.0), _entry("B", horse_no=2, carried=57.0),
        _entry("C", horse_no=3, carried=56.0),
        _entry("D", race_id=OTHER_RACE, carried=50.0),  # 別のレースの馬とは比べない
    ]
    features = _build(_records(entries, past_runs=runs))
    assert features["近5走の平均着差のレース内順位"].tolist()[:3] == [1, 1, 3]
    assert features["斤量とレースの平均との差"].tolist() == [-1.0, 1.0, 0.0, 0.0]


def test_class_order_is_fixed_for_ungraded_stakes_and_unknown():
    entries = [_entry("A", class_order=14), _entry("B", class_order=99), _entry("C", class_order=10)]
    ungraded_stakes, unknown, g1 = _build(_records(entries))["クラス"].tolist()
    assert ungraded_stakes == 8.0 and np.isnan(unknown) and g1 == 10.0


def test_undecided_going_becomes_missing():
    features = _build(_records([_entry("A", condition="?")]))
    assert pd.isna(features.loc[0, "馬場状態"])


def test_types_follow_the_catalog_and_timing():
    features = _build(_records([_entry("A")]), PredictionTiming.THURSDAY)
    assert list(features.columns) == list(PredictionTiming.THURSDAY.feature_columns())
    for name in features.columns:
        is_categorical = name in CATEGORICAL_FEATURES
        assert pd.api.types.is_string_dtype(features[name]) is is_categorical, name
    assert len(_build(_records([_entry("A")])).columns) == len(FEATURE_NAMES)
