"""買い目ごとの確定オッズを読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from ..betting import TicketType
from .final_odds_repository import _ANNOUNCED, _FINAL_STAGES, _ODDS_SCALE, COMBO, ODDS

#: 買い目の表を一時的に登録する名前。
_TICKETS = "ticket_odds_wanted"


class TicketOddsRepository:
    """1つの券種の、指定した買い目（レースID と組番）だけの確定オッズを読む（``o1``〜``o6``）。

    ``FinalOddsRepository`` は期間の全部の組を読むが、3連単の子の表は1レースに数千行あり、数年ぶんを読むと重い。
    こちらは買い目の表（列 ``race_id``・``combo``。組番は馬番を2桁ずつ並べた文字列）を一時表にして、その組だけを返す。
    親をデータ区分 4・5（確定）に絞って発表月日時分で子と結ぶのは ``FinalOddsRepository`` と同じ。
    複勝・ワイドは最低オッズ。無投票・取消の組は返さない（トリガミの確かめは、買えない組を外してから行う）。
    列は ``race_id``・``combo``・``odds``。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, ticket_type: TicketType) -> None:
        self._con = con
        self._ticket_type = ticket_type

    def read(self, tickets: pd.DataFrame) -> pd.DataFrame:
        spec = self._ticket_type.spec
        odds_column = "最低オッズ" if spec.has_odds_range else "オッズ"
        parent = facts.optional_relation(self._con, spec.odds_parent, (*keys.RACE_KEY, "データ区分", "データ作成年月日", _ANNOUNCED))
        child = facts.optional_relation(self._con, spec.odds_table, (*keys.RACE_KEY, _ANNOUNCED, spec.combo_column, odds_column))
        join = " AND ".join(f"{keys.col(column, 'o')} = {keys.col(column, 'h')}" for column in (*keys.RACE_KEY, _ANNOUNCED))
        wanted = tickets[["race_id", "combo"]].drop_duplicates().astype(str)
        self._con.register(_TICKETS, wanted)
        sql = f"""
        WITH final_header AS (
            SELECT {keys.key_list('h')}, {keys.col(_ANNOUNCED, 'h')}
            FROM {parent} AS h
            WHERE {keys.col('データ区分', 'h')} IN {keys.sql_list(_FINAL_STAGES)} AND {facts.venue_filter(self._con, 'h')}
              AND {keys.rid_expr('h')} IN (SELECT race_id FROM {_TICKETS})
            {keys.latest_qualify(keys.RACE_KEY, 'h')}
        ), odds AS (
            SELECT {keys.rid_expr('o')} AS race_id, trim({keys.col(spec.combo_column, 'o')}) AS {COMBO},
                   NULLIF(TRY_CAST({keys.col(odds_column, 'o')} AS INTEGER), 0) / {_ODDS_SCALE} AS {ODDS}
            FROM {child} AS o
            JOIN final_header AS h ON {join}
        )
        SELECT t.race_id, t.{COMBO}, odds.{ODDS}
        FROM {_TICKETS} AS t
        JOIN odds ON odds.race_id = t.race_id AND odds.{COMBO} = t.{COMBO}
        WHERE odds.{ODDS} IS NOT NULL
        ORDER BY t.race_id, t.{COMBO}
        """
        try:
            return self._con.execute(sql).df()
        finally:
            self._con.unregister(_TICKETS)
