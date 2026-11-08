"""テストで使う架空の出走の表（``RunnerFactsRepository`` と同じ列）。値は架空。"""

from __future__ import annotations

import pandas as pd

from 超荒れの展開と適性から大穴を当てる.analysis.repository.runner_facts_repository import COLUMNS

#: レースごとの着順（馬番 1〜12 の順）。人気 = 馬番。2月は大穴（10・11番人気）が1・2着、4月は 1〜3着が全部大穴。
FINISHES: dict[str, list[int]] = {
    "2024010106010101": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "2024020106010101": [3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2, 12],
    "2024030106010101": [2, 1, 3, 4, 5, 6, 7, 8, 9, 10, 12, 11],
    "2024040106010101": [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3],
}
FIELD = 12
LAST_RACE = "2024040106010101"


def history() -> pd.DataFrame:
    """4レース × 12頭。同じ12頭が毎回出る（馬番 = 人気 = 馬の番号）。3月・4月はハンデ戦、ほかは定量。"""
    rows = []
    for index, (race_id, finishes) in enumerate(FINISHES.items()):
        handicap = index >= 2
        for horse_no in range(1, FIELD + 1):
            row = {column: None for column in COLUMNS}
            finish = finishes[horse_no - 1]
            row.update({
                "race_id": race_id, "race_date": f"2024-0{index + 1}-01", "year": 2024.0, "venue": "中山", "race_no": 1.0,
                "surface": "芝", "course": "芝・右", "distance_m": 1600.0, "condition": "良", "class_name": "3勝クラス",
                "class_order": 5.0, "weight_type": "ハンデ" if handicap else "定量", "field_size": float(FIELD),
                "frame_no": float((horse_no + 1) // 2), "horse_no": float(horse_no), "horse_id": f"h{horse_no:02d}",
                "horse_name": f"馬{horse_no}", "jockey": "騎手", "carried": 57.0 - (horse_no % 4 if handicap else 0),
                "body_weight": 480.0, "popularity": float(horse_no), "win_odds": float(horse_no * 3), "finish": float(finish),
                "corner1": float(finish), "corner2": float(finish), "corner3": float(finish), "corner4": float(finish),
                "first_corner_rank": float(horse_no if index < 3 else FIELD + 1 - horse_no), "last3f_rank": float(finish),
                "style": "先行", "first3f": 35.0, "last3f_race": 35.0, "class_change": "同級", "runs_before": float(index),
                "course_runs_before": float(index), "course_places_before": 0.0, "dist_wins_before": 0.0, "cond_places_before": 0.0,
                "apprentice": "減量なし", "style_before": "差し" if horse_no > 6 else "先行", "lead_candidates": 1.0,
            })
            rows.append(row)
    return pd.DataFrame(rows)


def side_tables() -> dict[str, pd.DataFrame]:
    """回顧・展開の予想・締め切り前の人気の表（4月のレースだけペースと予想がある）。"""
    return {
        "reviews": pd.DataFrame({"race_id": [LAST_RACE], "pace": ["ハイ"], "tilt_inner": [0.2], "tilt_front": [0.1]}),
        "race_forecasts": pd.DataFrame({"race_id": [LAST_RACE], "p_slow": [0.1], "p_even": [0.3], "p_high": [0.6]}),
        "horse_forecasts": pd.DataFrame({"race_id": [LAST_RACE] * 2, "horse_id": ["h10", "h01"], "p_leader": [0.1, 0.5],
                                         "p_front": [0.2, 0.9], "p_middle": [0.2, 0.1], "p_back": [0.6, 0.0]}),
        "pre_close": pd.DataFrame({"race_id": [LAST_RACE], "horse_no": [10.0], "pre_close_odds": [25.0], "pre_close_popularity": [9.0]}),
    }
