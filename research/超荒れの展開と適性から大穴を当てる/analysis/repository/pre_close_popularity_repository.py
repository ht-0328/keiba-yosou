"""締め切り前の単勝オッズのいちばん新しい断面から、馬ごとの人気を読む（1 SQL）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys

_HEADER_TABLE = "o1"
_ODDS_TABLE = "o1__単勝オッズ"
_ANNOUNCED = "発表月日時分"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", _ANNOUNCED)
_ODDS_COLUMNS = (*keys.RACE_KEY, _ANNOUNCED, "馬番", "オッズ", "人気順")


@dataclass(frozen=True)
class PreClosePopularityRepository:
    """``date_from`` 以降のレースごとに、締め切り前の断面（データ区分 1〜3）のいちばん新しい発表月日時分の単勝オッズと人気。

    元DB に締め切り前の断面が残っているのは 2025年からなので、それより前のレースは行が無い。列は race_id・horse_no・
    pre_close_odds（倍）・pre_close_popularity。オッズの無い馬（取消・無投票）は入れない。
    """

    con: duckdb.DuckDBPyConnection

    def load(self, date_from: date) -> pd.DataFrame:
        header = facts.optional_relation(self.con, _HEADER_TABLE, _HEADER_COLUMNS)
        odds = facts.optional_relation(self.con, _ODDS_TABLE, _ODDS_COLUMNS)
        announced = keys.q(_ANNOUNCED)
        odds_value = f"TRY_CAST(NULLIF(o.{keys.q('オッズ')}, '{keys.NO_ODDS}') AS INTEGER)"
        sql = f"""
        WITH latest AS (
            SELECT {keys.rid_expr('h')} AS rid, max(h.{announced}) AS announced_at
            FROM {header} AS h
            WHERE h.{keys.q('データ区分')} IN {keys.sql_list(keys.ODDS_BEFORE_FINAL_STAGES)}
              AND h.{keys.q('開催年')} || h.{keys.q('開催月日')} >= ?
            GROUP BY 1
        )
        SELECT l.rid AS race_id, TRY_CAST(o.{keys.q('馬番')} AS DOUBLE) AS horse_no,
               {odds_value} / 10.0 AS pre_close_odds, TRY_CAST(o.{keys.q('人気順')} AS DOUBLE) AS pre_close_popularity
        FROM latest AS l
        JOIN {odds} AS o ON {keys.rid_expr('o')} = l.rid AND o.{announced} = l.announced_at
        WHERE {odds_value} IS NOT NULL AND {odds_value} > 0
        ORDER BY 1, 2
        """
        return self.con.execute(sql, [date_from.strftime("%Y%m%d")]).df()
