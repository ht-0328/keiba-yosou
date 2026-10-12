"""第1段: 保存した今の予想から、レースごとの「予想が見た 1,000倍以上になる確率」を作る（docs/06 の 2）。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID
from yosou.upset_premise.selection import BigPayoutChance

from .big_combo_odds import BigComboOdds
from .race_horses_builder import RaceHorsesBuilder

#: 作る列の名前。
CHANCE = "予想が見た1,000倍以上になる確率"


class BigChanceTable:
    """今の予想（区切りごとに学んだ1着と3着以内の予測。``RaceHorsesBuilder``）と、元DB の3連単の確定オッズから、
    レースごとに本番と同じ ``BigPayoutChance`` を出す。

    1,000倍以上の組のオッズは1年ずつ読み（``BigComboOdds``）、年ごとに確率を出して捨てる（全部を持つと重いため）。
    返すのは レースID → 確率（予想の無いレースは入らない）。
    """

    def __init__(self, builder: RaceHorsesBuilder) -> None:
        self._builder = builder
        self._chance = BigPayoutChance()

    def build(self, con: duckdb.DuckDBPyConnection, races: pd.DataFrame) -> pd.Series:
        """``races``（レースID・開催日）のレースの確率。"""
        parts = []
        for year, part in races.groupby(races[RACE_DATE].dt.year):
            odds = BigComboOdds.read(con, part)
            horses = self._builder.build(part[RACE_ID])
            values = {race_id: self._chance.of(horses[race_id], odds[race_id]) for race_id in part[RACE_ID]
                      if race_id in horses and race_id in odds}
            parts.append(pd.Series(values, dtype=float, name=CHANCE))
            print(f"  {year}年: {len(values)}レースの予想が見た確率を出しました", flush=True)
        return pd.concat(parts) if parts else pd.Series(dtype=float, name=CHANCE)
