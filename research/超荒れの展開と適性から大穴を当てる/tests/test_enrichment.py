"""出走の表に列を足す部品を、架空の値で確かめる。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.carried_weight_history import CarriedWeightHistory
from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.carried_weight_in_race import CarriedWeightInRace
from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.pace_attachment import PaceAttachment
from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.recent_form import RecentForm
from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.runner_enrichment import RunnerEnrichment, SideTables
from 超荒れの展開と適性から大穴を当てる.analysis.enrichment.running_position import RunningPosition

from .frames import LAST_RACE, history, side_tables


def _one_horse() -> pd.DataFrame:
    """1頭の5走（新しい走ほど下）。"""
    return pd.DataFrame({
        "race_id": ["r1", "r2", "r3", "r4", "r5"], "race_date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"],
        "horse_id": ["h"] * 5, "carried": [56.0, 55.0, 57.0, 55.0, 54.0], "finish": [2.0, 9.0, 1.0, 5.0, 3.0],
        "popularity": [3.0, 8.0, 2.0, 6.0, 11.0], "class_name": ["1勝", "2勝", "2勝", "3勝", "3勝"],
    })


def test_斤量の前走との差と同じ斤量の実績は今回より前の走だけから作る():
    frame = CarriedWeightHistory().add(_one_horse()).set_index("race_id")
    assert frame.loc["r2", "carried_change"] == -1.0
    assert pd.isna(frame.loc["r1", "carried_change"])
    assert frame.loc["r4", "same_carried_runs"] == 1.0          # 55kg は r2 で1回
    assert frame.loc["r4", "same_carried_places"] == 0.0        # r2 は9着
    assert frame.loc["r5", "heavier_places"] == 2.0             # 54kg より重い斤量で3着以内は r1・r3
    assert frame.loc["r3", "heavier_places"] == 0.0             # 57kg より重い斤量の好走は無い


def test_レースの中の斤量はトップとの差と平均との差():
    runners = pd.DataFrame({"race_id": ["a"] * 3, "carried": [58.0, 55.0, 52.0], "body_weight": [500.0, 0.0, 460.0]})
    frame = CarriedWeightInRace().add(runners)
    assert frame["carried_vs_top"].tolist() == [0.0, -3.0, -6.0]
    assert frame["carried_vs_mean"].tolist() == [3.0, 0.0, -3.0]
    assert frame["carried_spread"].tolist() == [6.0] * 3
    assert pd.isna(frame.loc[1, "carried_ratio_vs_mean"])       # 馬体重 0 は欠損値


def test_位置は最初のコーナーから決め_いつもとの差は近走の平均と比べる():
    runs = pd.DataFrame({
        "race_id": ["r1", "r2", "r3"], "race_date": ["2024-01-01", "2024-02-01", "2024-03-01"], "horse_id": ["h"] * 3,
        "first_corner_rank": [13.0, 12.0, 1.0], "corner4": [13.0, 10.0, 2.0], "field_size": [13.0] * 3, "horse_no": [1.0, 7.0, 13.0],
    })
    frame = RunningPosition().add(runs).set_index("race_id")
    assert frame.loc["r3", "result_style"] == "逃げ"
    assert frame.loc["r1", "result_style"] == "追込"
    assert frame.loc["r3", "position_shift"] == "いつもより前"
    assert pd.isna(frame.loc["r1", "position_shift"])            # 近走が無い
    assert frame["horse_side"].tolist() == ["内", "中", "外"]
    assert frame.loc["r3", "corner4_group"] == "前"


def test_展開の予想は区分と結果との違いを付ける():
    runners = pd.DataFrame({"race_id": ["a", "b", "c"], "horse_id": ["h1", "h2", "h3"]})
    reviews = pd.DataFrame({"race_id": ["a", "b"], "pace": ["ハイ", "スロー"], "tilt_inner": [0.0, 0.0], "tilt_front": [0.0, 0.0]})
    races = pd.DataFrame({"race_id": ["a", "b"], "p_slow": [0.1, 0.3], "p_even": [0.3, 0.3], "p_high": [0.6, 0.4]})
    horses = pd.DataFrame({"race_id": ["a"], "horse_id": ["h1"], "p_leader": [0.1], "p_front": [0.7], "p_middle": [0.2], "p_back": [0.1]})
    frame = PaceAttachment().add(runners, reviews, races, horses).set_index("race_id")
    assert frame.loc["a", "forecast_band"] == "ハイ予想"
    assert frame.loc["a", "pace_vs_forecast"] == "予想どおり"
    assert frame.loc["b", "forecast_pace"] == "ハイ"
    assert frame.loc["b", "pace_vs_forecast"] == "予想より遅い"
    assert frame.loc["c", "forecast_band"] == "予測なし"
    assert frame.loc["a", "expected_place"] == "前の見込み"
    assert frame.loc["b", "expected_place"] == "予測なし"


def test_近走は2走前と3走前の着順と人気():
    frame = RecentForm().add(_one_horse()).set_index("race_id")
    assert frame.loc["r4", "prev2_finish"] == 9.0
    assert frame.loc["r4", "prev3_popularity"] == 3.0
    assert frame.loc["r4", "prev_class_name"] == "2勝"


def test_流れは期間で絞り_大穴と期待の率と締め切り前の人気を付ける():
    frame = RunnerEnrichment(date(2024, 2, 1)).build(history(), SideTables(**side_tables()))
    assert frame["race_date"].min() == "2024-02-01"
    assert int(frame["longshot"].sum()) == 3 * 3                  # 3レース × 10〜12番人気
    last = frame.loc[frame["race_id"] == LAST_RACE].set_index("horse_no")
    assert not last.loc[10.0, "pre_close_longshot"]               # 締め切り前は9番人気
    assert pd.isna(last.loc[11.0, "pre_close_longshot"])          # 締め切り前の断面が無い馬
    assert last.loc[10.0, "expected_place"] == "後ろの見込み"
    assert last.loc[1.0, "forecast_band"] == "ハイ予想"
    assert int((frame["handicap"] == "ハンデ戦").sum()) == 24
    assert frame["expected_top3"].between(0, 1).all()
    assert frame.loc[frame["race_id"] == "2024020106010101", "carried_change"].eq(0.0).all()
    assert frame["period"].unique().tolist() == ["2021年〜"]       # 2024年は後半の年
