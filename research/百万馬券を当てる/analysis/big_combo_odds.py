"""選んだレースの、1,000倍以上の3連単の組の確定オッズを、小さい表で持つ。"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import date

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.dataset import RACE_DATE, RACE_ID
from yosou.shared.repository import FinalOddsRepository, RaceDayRange
from yosou.shared.repository.final_odds_repository import COMBO, ODDS
from yosou.upset_premise.betting import BIG_ODDS

#: 表の列の名前（馬番3つとオッズ）。
_FIRST, _SECOND, _THIRD, _ODDS = "1着", "2着", "3着", "オッズ"
#: 組番の1頭ぶんの桁数（馬番2桁）。
_DIGITS = 2


class BigComboOdds(Mapping[str, dict[tuple[int, ...], float]]):
    """レースID → 組（1着・2着・3着の馬番）→ 確定オッズ として引ける、1,000倍以上の組だけの表。

    一律の買い方は 1,000倍未満の組を買わないので、それ以外を持たない。3連単の組は1レース数千あり、
    レースごとの辞書で全部持つと重いため、1行 = 1組の小さい表（馬番は int8・オッズは float32）で持ち、
    引かれたレースだけ辞書にする。``read`` が元DB から、選んだレースのある年ごとに読む（1年ずつ読むのは、
    3連単の組が1年で数百万行あるため）。
    """

    def __init__(self, table: pd.DataFrame) -> None:
        self._table = table
        self._by_race = {race_id: rows for race_id, rows in table.groupby(RACE_ID, observed=True)}

    @classmethod
    def read(cls, con: duckdb.DuckDBPyConnection, races: pd.DataFrame, min_odds: float = BIG_ODDS) -> BigComboOdds:
        """選んだレース（``races`` の レースID・開催日）の、``min_odds`` 倍以上の組の確定オッズを元DB から読む。"""
        wanted = set(races[RACE_ID])
        years = sorted(int(year) for year in races[RACE_DATE].dt.year.unique())
        parts = [cls._year(con, year, wanted, min_odds) for year in years]
        return cls(pd.concat(parts, ignore_index=True) if parts else cls.empty_table())

    @staticmethod
    def empty_table() -> pd.DataFrame:
        return pd.DataFrame({RACE_ID: pd.Series(dtype=str), _FIRST: pd.Series(dtype=np.int8), _SECOND: pd.Series(dtype=np.int8),
                             _THIRD: pd.Series(dtype=np.int8), _ODDS: pd.Series(dtype=np.float32)})

    @property
    def table(self) -> pd.DataFrame:
        """持っている表（とっておく用）。"""
        return self._table

    def __getitem__(self, race_id: str) -> dict[tuple[int, ...], float]:
        rows = self._by_race[race_id]
        combos = zip(rows[_FIRST].tolist(), rows[_SECOND].tolist(), rows[_THIRD].tolist())
        return dict(zip(combos, rows[_ODDS].astype(float).tolist()))

    def __iter__(self) -> Iterator[str]:
        return iter(self._by_race)

    def __len__(self) -> int:
        return len(self._by_race)

    @staticmethod
    def _year(con: duckdb.DuckDBPyConnection, year: int, wanted: set[str], min_odds: float) -> pd.DataFrame:
        raw = FinalOddsRepository(con, TicketType.TRIFECTA).read(RaceDayRange(date(year, 1, 1), date(year, 12, 31)))
        raw = raw[raw["race_id"].isin(wanted) & raw[ODDS].ge(min_odds)]
        combo = raw[COMBO].astype(str)
        print(f"  3連単 {year}年: {raw['race_id'].nunique()}レースの {min_odds:,.0f}倍以上の組を読みました", flush=True)
        return pd.DataFrame({
            RACE_ID: raw["race_id"].to_numpy(), _FIRST: combo.str[0:_DIGITS].astype(np.int8).to_numpy(),
            _SECOND: combo.str[_DIGITS:2 * _DIGITS].astype(np.int8).to_numpy(), _THIRD: combo.str[2 * _DIGITS:3 * _DIGITS].astype(np.int8).to_numpy(),
            _ODDS: raw[ODDS].astype(np.float32).to_numpy(),
        })
