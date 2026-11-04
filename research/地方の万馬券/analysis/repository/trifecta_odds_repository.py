"""3連単の確定オッズを、指定したレースの全部の組について読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from 共通 import keys

_HEAD, _DETAIL = "o6", "o6__3連単オッズ"
#: 確定オッズのデータ区分。
_FINAL = "5"
_RACES_VIEW = "_trifecta_odds_races"


@dataclass(frozen=True)
class TrifectaOddsRepository:
    """``race_id``（16桁の整数）・``first``・``second``・``third``（馬番）・``odds``（倍。発売の無い組は出ない）。"""

    con: duckdb.DuckDBPyConnection

    def load(self, race_ids: pd.Series) -> pd.DataFrame:
        self.con.register(_RACES_VIEW, pd.DataFrame({"race_id": race_ids.astype(str).unique()}))
        key_join = " AND ".join(f"d.{keys.q(name)} = h.{keys.q(name)}" for name in keys.RACE_KEY)
        sql = f"""
            SELECT CAST({keys.rid_expr('h')} AS BIGINT) AS race_id,
                   CAST(substr(d.組番, 1, 2) AS INTEGER) AS first, CAST(substr(d.組番, 3, 2) AS INTEGER) AS second,
                   CAST(substr(d.組番, 5, 2) AS INTEGER) AS third,
                   TRY_CAST(d.オッズ AS DOUBLE) / 10.0 AS odds
            FROM {_HEAD} h
            JOIN {keys.q(_DETAIL)} d ON {key_join} AND d.発表月日時分 = h.発表月日時分
            JOIN {_RACES_VIEW} r ON r.race_id = {keys.rid_expr('h')}
            WHERE h.データ区分 = '{_FINAL}' AND TRY_CAST(d.オッズ AS DOUBLE) > 0
        """
        try:
            return self.con.execute(sql).df()
        finally:
            self.con.unregister(_RACES_VIEW)
