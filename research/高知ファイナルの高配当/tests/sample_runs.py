"""テスト用の架空の高知の出走の行（``KochiRunsRepository`` が返す形）。値はすべて架空。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 高知ファイナルの高配当.analysis.final_race import RACE_NAME_KEY

#: 1日のレース数と1レースの頭数。
RACES_PER_DAY, FIELD_SIZE = 3, 10


def kochi_runs(days: int = 12) -> pd.DataFrame:
    """毎週1日・1日3レース・10頭。3つめのレースがファイナルレース。同じ馬が毎週同じ番号のレースに出る。"""
    rng = np.random.default_rng(0)
    rows = []
    for day_index in range(days):
        day = pd.Timestamp("2025-01-05") + pd.Timedelta(days=7 * day_index)
        for race_no in range(1, RACES_PER_DAY + 1):
            rows.extend(_race_rows(rng, day, race_no))
    return pd.DataFrame(rows)


def _race_rows(rng: np.random.Generator, day: pd.Timestamp, race_no: int) -> list[dict]:
    finishes = rng.permutation(FIELD_SIZE) + 1
    popularities = rng.permutation(FIELD_SIZE) + 1
    is_final = race_no == RACES_PER_DAY
    return [{
        "race_id": f"{day:%Y%m%d}54{race_no:02d}", "race_date": day.date(), "race_no": race_no,
        "race_name": f"{RACE_NAME_KEY}　Ｃ２" if is_final else "", "class_name": "C2", "class_order": 30,
        "distance_m": 1400 if race_no % 2 else 1300, "condition": "良", "field_size": FIELD_SIZE,
        "frame_no": min(8, number), "horse_no": number, "horse_id": f"h{race_no}-{number}", "sex": "牡", "age": 5,
        "jockey_code": f"j{(number + race_no) % 5}", "carried": 56.0, "weight_change": 0.0,
        "popularity": int(popularities[number - 1]), "win_odds": float(popularities[number - 1]) * 2.0,
        "finish": int(finishes[number - 1]), "time_diff": float(finishes[number - 1] - 1) * 0.3,
        "corner4": int(finishes[number - 1]), "first_corner_rank": number, "last3f_rank": int(finishes[number - 1]),
        "win_payout": 500.0 if finishes[number - 1] == 1 else 0.0, "place_payout": 200.0 if finishes[number - 1] <= 3 else 0.0,
        "prev_finish": 5.0, "prev_time_diff": 1.0, "prev_corner4": 5.0, "interval_days": 7.0,
        "jockey_change": "継続", "apprentice": "減量なし", "best_time_unit_rank": float(number),
    } for number in range(1, FIELD_SIZE + 1)]
