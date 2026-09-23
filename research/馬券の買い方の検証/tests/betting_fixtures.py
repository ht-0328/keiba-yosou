"""テストで使う架空の runners（1レース16頭）を作る部品。値はすべて作りもの。

人気順位 = 馬番。近走と適性の確率は人気順に下がる（本命 = 1番人気）。危険確率は 1〜5番人気だけにあり、4・5番人気が危険（0.6以上）。
穴馬の確率は 6番人気以下だけにあり、6〜9番人気が中穴、10番人気以下が大穴。単勝オッズは 人気 × 1.5倍、複勝オッズ（下限）は 1 + 0.5 × 人気。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 馬券の買い方の検証.analysis import column_names as names

RACE_ID = "2025070605010101"
FIELD_SIZE = 16
#: 1〜5番人気の危険確率（4・5番人気が 0.6 以上 = 危険）。
DANGER_BY_POPULARITY = {1: 0.3, 2: 0.4, 3: 0.5, 4: 0.7, 5: 0.8}


def runners(*, top_odds: float = 1.5, top_danger: float = 0.3, race_id: str = RACE_ID, race_date: str = "2025-07-06") -> pd.DataFrame:
    """16頭の runners。``top_odds`` は1番人気の単勝オッズ、``top_danger`` は1番人気の危険確率。"""
    horses = list(range(1, FIELD_SIZE + 1))
    danger = {**DANGER_BY_POPULARITY, 1: top_danger}
    rows = pd.DataFrame({
        names.RACE_ID: race_id, names.RACE_DATE: pd.Timestamp(race_date), names.HORSE_NO: horses,
        names.FINISH: [4, 2, 3, 6, 7, 1, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16],
        names.WIN_ODDS: [top_odds if horse == 1 else horse * 1.5 for horse in horses],
        names.POPULARITY: horses,
        names.WIN_PAYOUT: [900 if horse == 6 else 0 for horse in horses],
        names.PLACE_PAYOUT: [300 if horse in (2, 3, 6) else 0 for horse in horses],
        names.FORM_PROB: [round(0.9 - 0.05 * horse, 3) for horse in horses],
        names.DANGER_PROB: [danger.get(horse, np.nan) for horse in horses],
        names.LONGSHOT_PROB: [round(0.5 - 0.03 * horse, 3) if horse >= 6 else np.nan for horse in horses],
        names.LONGSHOT_ZONE: [("中穴" if horse <= 9 else "大穴") if horse >= 6 else None for horse in horses],
        names.PLACE_ODDS: [1.0 + 0.5 * horse for horse in horses],
    })
    return rows
