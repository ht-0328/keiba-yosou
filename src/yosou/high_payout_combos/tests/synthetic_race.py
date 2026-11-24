"""テスト用の架空のレース（馬ごとの表と5券種の板）を作る関数。値は全部架空。"""

from __future__ import annotations

from itertools import combinations, permutations

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from ..dataset import PayoutBand

RACE = "2025010506010101"
#: 架空の4頭。馬番 → 値。人気は馬番の逆順（4番が1番人気）にして、馬番の順と人気の順が違うようにしてある。
WIN_PROBABILITY = {1: 0.4, 2: 0.3, 3: 0.2, 4: 0.1}
TOP3_PROBABILITY = {1: 0.9, 2: 0.8, 3: 0.7, 4: 0.6}
MARKET_WIN = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
MARKET_TOP3 = {1: 0.6, 2: 0.7, 3: 0.8, 4: 0.9}
WIN_ODDS = {1: 8.0, 2: 4.0, 3: 2.7, 4: 2.0}
PLACE_ODDS = {1: (2.0, 4.0), 2: (1.5, 2.5), 3: (1.2, 1.8), 4: (1.0, 1.4)}
POPULARITY = {1: 4, 2: 3, 3: 2, 4: 1}
MARK = {1: "◎", 2: "○", 3: "▲", 4: "消"}
WIN_VALUE = {1: 1.2, 2: 0.9, 3: 0.8, 4: 0.5}
#: テストで使う、全部の組が対象になる広い帯（学ぶ下限 1倍・高配当の線 2倍・上限 10万倍）。
ALL_TICKET_TYPES = (TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA, TicketType.TRIO, TicketType.TRIFECTA)
WIDE_OPEN_BANDS = {ticket_type: PayoutBand(ticket_type, 1.0, 2.0, 100_000.0) for ticket_type in ALL_TICKET_TYPES}


def horses(race_id: str = RACE) -> pd.DataFrame:
    """架空の4頭の馬ごとの表。4番は1番人気で危険な人気馬（消）、1番は ◎ で単勝の期待値 1.2。"""
    numbers = list(WIN_PROBABILITY)
    return pd.DataFrame({
        "race_id": race_id, "race_date": pd.Timestamp("2025-01-05"), "horse_no": numbers,
        "probability": [TOP3_PROBABILITY[no] for no in numbers], "win_probability": [WIN_PROBABILITY[no] for no in numbers],
        "market_win": [MARKET_WIN[no] for no in numbers], "market_top3": [MARKET_TOP3[no] for no in numbers],
        "win_odds": [WIN_ODDS[no] for no in numbers],
        "place_odds_low": [PLACE_ODDS[no][0] for no in numbers], "place_odds_high": [PLACE_ODDS[no][1] for no in numbers],
        "popularity": [POPULARITY[no] for no in numbers], "rank": numbers,
        "is_danger": [no == 4 for no in numbers], "danger_score": [0.3 if no == 4 else np.nan for no in numbers],
        "mark": [MARK[no] for no in numbers], "updown": [0.1, 0.0, -0.1, -0.2],
        "win_value": [WIN_VALUE[no] for no in numbers], "place_value": [1.1, 1.0, 0.9, 0.8],
    })


def odds_of(ticket_type: TicketType, combo: tuple[int, ...]) -> float:
    """架空のオッズ。組ごとに違う値になるように、馬番から決める（ワイドは小さめ、3連単は大きめ）。"""
    base = {TicketType.WIDE: 2.0, TicketType.QUINELLA: 5.0, TicketType.EXACTA: 10.0, TicketType.TRIO: 3.0, TicketType.TRIFECTA: 20.0}
    steps = (3.0, 2.0, 1.0)
    return base[ticket_type] + sum(step * number for step, number in zip(steps, combo))


def combo_text(combo: tuple[int, ...]) -> str:
    """馬番の並びを組番にする。例: (1, 5) → ``0105``。"""
    return "".join(f"{number:02d}" for number in combo)


def combos_of(ticket_type: TicketType, numbers: tuple[int, ...] = (1, 2, 3, 4)) -> list[tuple[int, ...]]:
    """その券種の全部の組（順不同の券種は馬番の小さい順）。"""
    count = ticket_type.spec.horse_count
    if ticket_type.spec.is_ordered:
        return list(permutations(numbers, count))
    return list(combinations(numbers, count))


def board(ticket_type: TicketType, race_id: str = RACE, numbers: tuple[int, ...] = (1, 2, 3, 4)) -> pd.DataFrame:
    """その券種の板（列 race_id・combo・odds）。"""
    combos = combos_of(ticket_type, numbers)
    return pd.DataFrame({
        "race_id": race_id, "combo": [combo_text(combo) for combo in combos],
        "odds": [odds_of(ticket_type, combo) for combo in combos],
    })


def boards(race_id: str = RACE) -> dict[TicketType, pd.DataFrame]:
    """5券種の板。"""
    return {ticket_type: board(ticket_type, race_id) for ticket_type in ALL_TICKET_TYPES}


def market_probability(ticket_type: TicketType, combo: tuple[int, ...]) -> float:
    """その券種の市場の確率 q を、板から素直に計算した値（1 ÷ オッズ をレースで合計 1、ワイドは 3 にそろえる）。"""
    total = sum(1.0 / odds_of(ticket_type, each) for each in combos_of(ticket_type))
    winners = 3.0 if ticket_type is TicketType.WIDE else 1.0
    return 1.0 / odds_of(ticket_type, combo) / total * winners
