"""型の決めごとと表を、架空の値で確かめる。"""

from __future__ import annotations

import pandas as pd

from WIN5で人気薄の勝ち馬を狙う.analysis.tables.case_count_table import CaseCountTable
from WIN5で人気薄の勝ち馬を狙う.analysis.tables.flag_share_table import FlagShareTable
from WIN5で人気薄の勝ち馬を狙う.analysis.tables.longshot_rank_table import LongshotRankTable
from WIN5で人気薄の勝ち馬を狙う.analysis.theory.race_table import RaceTable
from WIN5で人気薄の勝ち馬を狙う.analysis.theory.race_type_catalog import RACE_TYPES
from WIN5で人気薄の勝ち馬を狙う.analysis.theory.runner_type_catalog import NO_TYPE, RUNNER_TYPES
from WIN5で人気薄の勝ち馬を狙う.analysis.theory.runner_type_flags import TYPE_LABELS, RunnerTypeFlags


def _horse(**over: object) -> dict[str, object]:
    """どの型にも当てはまらない人気薄1頭。``over`` で値を替える。"""
    base: dict[str, object] = {
        "best_placed_class": 2.0, "class_order": 5.0, "prev_finish": 4.0, "prev_time_diff": 1.0, "surface_change": "同じ",
        "distance_m": 1600.0, "prev_distance_m": 1600.0, "prev_condition": "良", "condition": "良", "prev_class_order": 5.0,
        "surface_places_before": 0.0, "style_before": "差し", "lead_candidates": 2.0, "weight_type": "定量", "carried_gap": 0.0,
        "jockey_rate": 0.05, "prev_jockey_rate": 0.05, "front_places_before": 0.0, "back_places_before": 0.0, "prev_style": "差し",
    }
    return {**base, **over}


def test_馬の側の型の当てはまり():
    runners = pd.DataFrame([
        _horse(),
        _horse(best_placed_class=6.0, prev_finish=9.0),                                       # A
        _horse(style_before="先行", lead_candidates=1.0),                                     # C
        _horse(front_places_before=3.0, back_places_before=1.0, prev_finish=10.0),            # G（と前走6着以下）
        _horse(weight_type="ハンデ", carried_gap=-1.5, jockey_rate=0.12),                      # E・F
    ])
    flags = RunnerTypeFlags().add(runners)
    assert flags[NO_TYPE].tolist() == [True, False, False, False, False]
    assert flags[TYPE_LABELS].tolist() == ["Z", "A", "C", "G", "E・F"]
    assert len(RUNNER_TYPES) == 7


def test_レースの表とレースの型():
    runners = pd.DataFrame({
        "race_id": ["a", "a", "b", "b"], "finish": [1.0, 2.0, 2.0, 1.0], "popularity": [12.0, 1.0, 1.0, 2.0],
        "race_date": ["2024-01-01"] * 4, "year": [2024.0] * 4, "venue": ["東京"] * 4, "surface": ["芝"] * 4,
        "distance_m": [1600.0] * 4, "condition": ["良"] * 4, "class_name": ["G3"] * 4, "weight_type": ["ハンデ", "ハンデ", "定量", "定量"],
        "field_size": [16.0, 16.0, 10.0, 10.0], "favorite_odds": [5.0, 5.0, 1.5, 1.5], "contenders": [4.0, 4.0, 2.0, 2.0],
        "top3_market": [0.5, 0.5, 0.8, 0.8], "longshot_market": [0.12, 0.12, 0.01, 0.01], "win5_leg": [1.0, 1.0, None, None],
    })
    races = RaceTable(10).build(runners)
    assert races.loc["a", "longshot_won"] and not races.loc["b", "longshot_won"]
    flags = {rule.name: rule.flags(races).tolist() for rule in RACE_TYPES}
    assert flags["R1 人気薄に票が残る"] == [True, False]
    assert flags["R3 ハンデ戦"] == [True, False]
    counts = CaseCountTable(10).build(races)[0]
    assert counts.rows[0][1:3] == [2, 1]          # 平地の全レース: 2レース中1レース
    assert counts.rows[1][1:3] == [1, 1]          # WIN5: 1レース中1レース


def test_手がかりの表は勝った馬の中の割合と市場との比を出す():
    longshots = pd.DataFrame([_horse(prev_finish=9.0, best_placed_class=6.0), _horse(), _horse(), _horse()])
    longshots["finish"] = [1.0, 5.0, 6.0, 7.0]
    longshots["market"] = [0.02, 0.02, 0.02, 0.02]
    table = FlagShareTable().build(longshots, RUNNER_TYPES[:1], "t")
    row = table.rows[0]
    assert row[2:6] == [1, 1, "100.0%", "25.0%"]
    assert row[6] == "4.00"
    assert row[7] == "50.00"


def test_人気薄の中の並べ方で勝ち馬を何頭目に置けたか():
    longshots = pd.DataFrame({
        "race_id": ["r"] * 3, "finish": [3.0, 1.0, 2.0], "model": [0.03, 0.02, 0.01], "market": [0.01, 0.03, 0.02],
        "uplift": [3.0, 0.67, 0.5],
        **{rule.name: [False] * 3 for rule in RUNNER_TYPES},
    })
    table = LongshotRankTable().build(longshots, "t")
    rows = {row[0]: row[1:] for row in table.rows}
    assert rows["今のモデルの1着の確率の順"][:2] == ["0.0%", "100.0%"]
    assert rows["人気の順（オッズから見た勝率の順）"][0] == "100.0%"
