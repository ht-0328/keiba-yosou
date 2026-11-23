"""テストで使う架空の材料の表（実データは使わない）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 地方の直前の買い目 import late_columns as c


def material(races: int = 1, heads: int = 6, seed: int = 0, start: str = "2024-01-01") -> pd.DataFrame:
    """``races`` レース × ``heads`` 頭。レースは1日に1つずつ。オッズと確率は乱数（種で決まる）。結果の列も付ける。"""
    rng = np.random.default_rng(seed)
    rows = []
    for index in range(races):
        day = pd.Timestamp(start) + pd.Timedelta(days=index)
        rid = f"{day:%Y%m%d}44010{1 + index % 9}{1 + index % 12:02d}"
        odds = np.round(rng.uniform(1.5, 60.0, heads), 1)
        share = (1 / odds) / (1 / odds).sum()
        winner = int(rng.choice(heads, p=share))
        for horse in range(heads):
            rows.append({c.RACE_ID: rid, c.HORSE_NO: horse + 1, c.RACE_DATE: f"{day:%Y-%m-%d}", c.FIELD_SIZE: heads,
                         c.ODDS_NOW: odds[horse], c.ODDS_A: odds[horse] * 1.1, c.ODDS_B: odds[horse] * 1.2, c.ODDS_FIRST: odds[horse] * 0.9,
                         c.ODDS_BACK_2: odds[horse] * 1.02, c.ODDS_BACK_5: odds[horse] * 1.05, c.ODDS_BACK_35: odds[horse] * 1.3,
                         c.PLACE_LOW: max(1.0, odds[horse] / 4), c.PLACE_HIGH: max(1.1, odds[horse] / 3),
                         c.PLACE_LOW_A: max(1.0, odds[horse] / 4) * 1.1,
                         c.WIN_MODEL: share[horse], c.TOP3_MODEL: min(0.95, share[horse] * 2.5), c.WIN_FREE: share[horse] * 0.9,
                         c.TOP3_FREE: min(0.95, share[horse] * 2.2), c.FINAL_ODDS: odds[horse] * 0.8, c.WON: int(horse == winner),
                         c.WIN_TEACHER: share[horse] * (1.5 if horse % 2 else 0.7)})
    return pd.DataFrame(rows)
