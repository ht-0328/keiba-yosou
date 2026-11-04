"""馬の事情と騎手の場内順位を、架空の出走の表で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 地方の万馬券.analysis.jockey_venue_rank import JOCKEY_VENUE_RANK, JockeyVenueRank
from 地方の万馬券.analysis.runner_circumstances import CIRCUMSTANCES, RunnerCircumstances


def _runners() -> pd.DataFrame:
    """1レース3頭。1頭目は遠征の人気馬、2頭目は転入初戦の穴馬、3頭目は中央所属。"""
    return pd.DataFrame({
        "race_id": ["r1"] * 3, "venue": ["大井"] * 3, "trainer_area": ["名古屋", "船橋", None],
        "affiliation": ["招待", "招待", "栗東"], "age": [5, 4, 3], "runs_before": [10, 0, 0],
        "interval_days": [7, 120, 14], "class_change": ["昇級", "前走なし", "同級"], "jockey_change": ["乗り替わり", "前走なし", "継続"],
        JOCKEY_VENUE_RANK: [1.0, np.nan, 12.0], "prev_finish": [1, np.nan, 7], "prev_time_diff": [-0.2, np.nan, 1.5],
        "prev_popularity": [1, np.nan, 8], "prev_corner4": [2, np.nan, 10], "prev_field_size": [12, np.nan, 12],
        "frame_no": [1, 8, 5], "venue_change": ["別", "前走なし", "同じ"], "distance_change": ["延長", "前走なし", "短縮"],
        "carried": [56.0, 54.0, 55.0], "weight_change": [2, -12, 0], "apprentice": ["減量なし", "減量あり", "減量なし"],
        "blinker": ["なし", "あり", "なし"], "sex": ["牡", "牝", "牡"], "mixed_sex": [True, True, True],
        "best_time_unit_rank": [1, np.nan, 3], "course_runs_before": [3, 0, 0],
        "popularity": [1, 8, 3], "win_odds": [2.0, 30.0, 5.0],
    })


def test_事情の列が全部付き_欠損は事情なしになる():
    table = RunnerCircumstances().attach(_runners())
    assert all(name in table.columns for name in CIRCUMSTANCES)
    assert table[list(CIRCUMSTANCES)].dtypes.eq(bool).all()


def test_遠征と転入初戦と中央所属():
    table = RunnerCircumstances().attach(_runners())
    assert list(table["遠征"]) == [True, False, False]        # 名古屋の調教師が大井へ。中央所属は遠征に数えない
    assert list(table["転入初戦"]) == [False, True, True]
    assert list(table["中央所属"]) == [False, False, True]


def test_前走の位置と騎手の場内順位と斤量():
    table = RunnerCircumstances().attach(_runners())
    assert list(table["前走は前にいた"]) == [True, False, False]
    assert list(table["前走は後ろにいた"]) == [False, False, True]
    assert list(table["騎手が場の上位3"]) == [True, False, False]
    assert list(table["騎手が場の圏外"]) == [False, True, True]
    assert list(table["斤量が重い"]) == [True, False, False]
    assert list(table["斤量が軽い"]) == [False, True, False]
    assert list(table["連闘"]) == [True, False, False]
    assert list(table["休み明け"]) == [False, True, False]
    assert list(table["馬体重の増減が大きい"]) == [False, True, False]


def test_騎手の場内順位は前の年の勝利数の順位():
    runs = pd.DataFrame({
        "year": [2024, 2024, 2024, 2025, 2025],
        "venue_code": ["44"] * 5, "jockey_code": ["a", "a", "b", "a", "b"],
        "finish": [1, 1, 1, 5, 1],
    })
    table = JockeyVenueRank().attach(runs)
    in_2025 = table[table["year"] == 2025].set_index("jockey_code")
    assert in_2025.loc["a", JOCKEY_VENUE_RANK] == 1      # 2024年に 2勝で 1位
    assert in_2025.loc["b", JOCKEY_VENUE_RANK] == 2
    assert table[table["year"] == 2024][JOCKEY_VENUE_RANK].isna().all()   # 2023年の記録が無いので欠損
