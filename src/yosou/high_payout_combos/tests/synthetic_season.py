"""テスト用の架空の数年ぶんのレース（馬ごとの表・5券種の板・払戻）と、その組の表を作る関数。値は全部、乱数で作った架空のもの。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from ..dataset import ComboTableBuilder, HitLabeler
from ..feature import HarvilleProbability
from ..repository import ComboTableRepository
from . import synthetic_race as race

#: 架空のシーズンの年と、1年のレースの数・1レースの頭数。
YEARS = (2021, 2022, 2023, 2024)
RACES_PER_YEAR = 40
HORSE_COUNT = 7
#: 表を作って学習まで通す券種（5つ全部だと時間がかかるので、組の少ないワイドと、組の多い3連単）。
TRAINED_TYPES = (TicketType.WIDE, TicketType.TRIFECTA)
_MARKS = ("◎", "○", "▲", "△", "☆", "注", "－")
#: 架空のオッズを作るときの払戻率と、架空の払戻の額（円）。
_PAYOUT_RATE = 0.75
_PAYOUT_YEN = 5_000


def race_ids(year: int) -> list[str]:
    """その年の架空のレースID（16桁）。"""
    return [f"{year}0105060101{index:02d}" for index in range(1, RACES_PER_YEAR + 1)]


def race_horses(race_id: str, race_date: pd.Timestamp, random: np.random.Generator) -> pd.DataFrame:
    """1レースの架空の馬ごとの表。予想の1着の確率と市場の勝率は、少しずれた別の値にする。"""
    numbers = np.arange(1, HORSE_COUNT + 1)
    win = random.dirichlet(np.full(HORSE_COUNT, 2.0))
    noisy = win * np.exp(random.normal(0.0, 0.3, HORSE_COUNT))
    market_win = noisy / noisy.sum()
    top3, market_top3 = np.clip(win * 2.5, None, 0.95), np.clip(market_win * 2.5, None, 0.95)
    win_rank = pd.Series(win).rank(ascending=False, method="first").astype(int).to_numpy()
    popularity = pd.Series(market_win).rank(ascending=False, method="first").astype(int).to_numpy()
    place_low = np.clip(0.6 / market_top3, 1.0, None)
    return pd.DataFrame({
        "race_id": race_id, "race_date": race_date, "horse_no": numbers,
        "probability": top3, "win_probability": win, "market_win": market_win, "market_top3": market_top3,
        "win_odds": 0.8 / market_win, "place_odds_low": place_low, "place_odds_high": place_low * 1.5,
        "popularity": popularity, "rank": win_rank,
        "is_danger": (popularity == 1) & (win_rank > 3), "danger_score": np.where(popularity <= 3, 0.2, np.nan),
        "mark": [_MARKS[min(rank, len(_MARKS)) - 1] for rank in win_rank], "updown": np.log(win / market_win),
        "win_value": win * 0.8 / market_win, "place_value": top3 * place_low,
    })


def year_horses(year: int, random: np.random.Generator) -> pd.DataFrame:
    """1年ぶんの架空の馬ごとの表。レースは1週おき。"""
    first_day = pd.Timestamp(year=year, month=1, day=5)
    races = [race_horses(race_id, first_day + pd.Timedelta(weeks=index), random) for index, race_id in enumerate(race_ids(year))]
    return pd.concat(races, ignore_index=True)


def race_board(ticket_type: TicketType, horses: pd.DataFrame) -> pd.DataFrame:
    """1レースの架空の板。オッズは、市場の勝率から Harville の式で出した確率の逆数に払戻率を掛けたもの（ワイドは小さめ）。"""
    shares = dict(zip(horses["horse_no"], horses["market_win"]))
    combos = race.combos_of(ticket_type, tuple(shares))
    numbers = np.array(combos)
    members = pd.Series(shares).reindex(numbers.ravel()).to_numpy().reshape(numbers.shape)
    harville = HarvilleProbability()
    probability = harville.in_order(members) if ticket_type.spec.is_ordered else harville.any_order(members)
    spread = 3.0 if ticket_type is TicketType.WIDE else 1.0
    return pd.DataFrame({
        "race_id": horses["race_id"].iloc[0], "combo": [race.combo_text(combo) for combo in combos],
        "odds": np.round(np.clip(_PAYOUT_RATE / (probability * spread), 1.1, None), 1),
    })


def boards_of(horses: pd.DataFrame) -> dict[TicketType, pd.DataFrame]:
    """何レースぶんかの馬ごとの表から、5券種の板。"""
    return {ticket_type: _board_of_races(ticket_type, horses) for ticket_type in race.ALL_TICKET_TYPES}


def _board_of_races(ticket_type: TicketType, horses: pd.DataFrame) -> pd.DataFrame:
    races = horses.groupby("race_id", sort=False)
    return pd.concat([race_board(ticket_type, each) for _, each in races], ignore_index=True)


def _payouts_of_races(ticket_type: TicketType, horses: pd.DataFrame, random: np.random.Generator) -> pd.DataFrame:
    races = horses.groupby("race_id", sort=False)
    return pd.concat([race_payouts(ticket_type, each, random) for _, each in races], ignore_index=True)


def race_payouts(ticket_type: TicketType, horses: pd.DataFrame, random: np.random.Generator) -> pd.DataFrame:
    """1レースの架空の払戻。上位3頭を、予想の1着の確率に応じた乱数で決める。"""
    top3 = [int(number) for number in random.choice(horses["horse_no"], size=3, replace=False, p=horses["win_probability"])]
    winners = {
        TicketType.EXACTA: [tuple(top3[:2])], TicketType.QUINELLA: [tuple(sorted(top3[:2]))],
        TicketType.TRIFECTA: [tuple(top3)], TicketType.TRIO: [tuple(sorted(top3))],
        TicketType.WIDE: [tuple(sorted(pair)) for pair in ((top3[0], top3[1]), (top3[0], top3[2]), (top3[1], top3[2]))],
    }[ticket_type]
    combos = [race.combo_text(combo) for combo in winners]
    return pd.DataFrame({"race_id": horses["race_id"].iloc[0], "combo": combos, "yen": _PAYOUT_YEN})


def write_year_tables(repository: ComboTableRepository, year: int, horses: pd.DataFrame, random: np.random.Generator) -> None:
    """1年ぶんの組の表（``TRAINED_TYPES`` の券種）を作って書く。"""
    tables = ComboTableBuilder(race.WIDE_OPEN_BANDS).build(horses, boards_of(horses), TRAINED_TYPES)
    race_dates = horses.groupby("race_id")["race_date"].first()
    for ticket_type, table in tables.items():
        payouts = _payouts_of_races(ticket_type, horses, random)
        with repository.writer(ticket_type, year) as writer:
            writer.write(HitLabeler().label(ticket_type, table, payouts, race_dates))


def write_season_tables(repository: ComboTableRepository) -> dict[int, pd.DataFrame]:
    """架空のシーズン（``YEARS``）の組の表を書き、年 → 馬ごとの表を返す。"""
    random = np.random.default_rng(7)
    horses_by_year = {year: year_horses(year, random) for year in YEARS}
    for year, horses in horses_by_year.items():
        write_year_tables(repository, year, horses, random)
    return horses_by_year
