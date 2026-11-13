"""今のモデルの予測の代わり（学習済みモデルを読まない）。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from yosou.shared.dataset import HORSE_NAME, HORSE_NO, RACE_ID
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.workflow import WIN_PROBABILITY

from .win5_sample import RACE_NUMBERS

#: 1着の確率を高めに見る馬番（どのレースでも）。上乗せが 1 を超える馬になる。
FAVORED_HORSE = 3
FAVOR = 1.5


class FakePrediction:
    """``FormAptitudePrediction.run`` と同じ形の表を返す代わり。1着の確率は、オッズから見た勝率（取り分を含む逆数）に、
    馬番 3 だけ 1.5 倍を掛けたもの（合計は 1 にならない。``RaceWinShare`` がそろえる）。呼ばれた（レースID, 時点）を覚える。"""

    def __init__(self, odds: dict[tuple[date, int], dict[int, float]]) -> None:
        self._odds = odds
        self.calls: list[tuple[str, PredictionTiming]] = []

    def run(self, con: duckdb.DuckDBPyConnection, race_id: str, timing: PredictionTiming) -> pd.DataFrame:
        self.calls.append((race_id, timing))
        day = date(int(race_id[:4]), int(race_id[4:6]), int(race_id[6:8]))
        leg_odds = self._odds[(day, RACE_NUMBERS.index(race_id[-2:]) + 1)]
        numbers = sorted(leg_odds)
        return pd.DataFrame({
            RACE_ID: race_id, HORSE_NO: numbers, HORSE_NAME: [f"ウマ{number:02d}" for number in numbers],
            WIN_ODDS: [leg_odds[number] for number in numbers],
            WIN_PROBABILITY: [0.8 / leg_odds[number] * (FAVOR if number == FAVORED_HORSE else 1.0) for number in numbers],
        })
