"""レースごとの、締め切り前の単勝オッズのいちばん新しい断面（``o1``・``o1__単勝オッズ``）を読む。"""

from __future__ import annotations

import duckdb

from 共通 import facts, keys
from 共通.race_signals.race_scope import RaceScope

#: オッズ1（単複枠）の親の表と、馬番ごとの単勝オッズが入る子の表。
_HEADER_TABLE = "o1"
_ODDS_TABLE = "o1__単勝オッズ"
_ANNOUNCED = "発表月日時分"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", _ANNOUNCED)
_ODDS_COLUMNS = (*keys.RACE_KEY, _ANNOUNCED, "馬番", "オッズ")


class AnnouncedOddsSummaryRepository:
    """範囲のレースごとに、締め切り前の単勝オッズ（データ区分 1〜3 の断面）のいちばん新しい発表月日時分と、
    その断面でオッズの付いている馬の数を読む。断面の選び方とオッズの読み方は ``AnnouncedOddsRepository``（1レースの全頭を読む）と同じ。
    表の無い DB では空の関係で代わりにする。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: RaceScope) -> dict[str, tuple[str, int]]:
        """rid → （発表月日時分, オッズの付いた馬の数）。締め切り前の断面の無いレースは入らない。"""
        header_table = facts.optional_relation(self._con, _HEADER_TABLE, _HEADER_COLUMNS)
        odds_table = facts.optional_relation(self._con, _ODDS_TABLE, _ODDS_COLUMNS)
        where, params = scope.where("h")
        announced_at = keys.q(_ANNOUNCED)
        odds_value = f"TRY_CAST(NULLIF(o.{keys.q('オッズ')}, '{keys.NO_ODDS}') AS INTEGER)"
        sql = f"""
        WITH latest AS (
            SELECT {keys.rid_expr('h')} AS rid, max(h.{announced_at}) AS announced_at
            FROM {header_table} AS h
            WHERE {where}
              AND h.{keys.q('データ区分')} IN {keys.sql_list(keys.ODDS_BEFORE_FINAL_STAGES)}
            GROUP BY 1
        )
        SELECT l.rid, l.announced_at, count(*) FILTER ({odds_value} IS NOT NULL)
        FROM latest AS l
        LEFT JOIN {odds_table} AS o ON {keys.rid_expr('o')} = l.rid AND o.{announced_at} = l.announced_at
        GROUP BY l.rid, l.announced_at
        """
        return {rid: (announced, count) for rid, announced, count in self._con.execute(sql, params).fetchall()}
