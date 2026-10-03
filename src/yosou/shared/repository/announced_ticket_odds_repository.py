"""締め切り前の、1つの券種の全部の組のオッズを読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from ..betting import TicketType
from .final_odds_repository import _ANNOUNCED, _ODDS_SCALE, COMBO, ODDS

#: 確定前の断面のデータ区分（1 中間・2 前日売最終・3 最終）。4 確定・5 確定(月曜)・9 中止は読まない。
_BEFORE_FINAL_STAGES: tuple[str, ...] = ("1", "2", "3")


class AnnouncedTicketOddsRepository:
    """締め切り前のオッズ（速報オッズ ``0B30`` や時系列オッズ）から、1レース・1券種のいちばん新しい断面を、1組1行で読む（``o1``〜``o6``）。

    今週の予想が、印のルールの買い目に期待値（組の確率 × オッズ）とトリガミの確かめを付けるのに使う。
    ``AnnouncedOddsRepository``（単勝だけ・馬番の列）と同じく、親をデータ区分 1〜3 に絞って発表月日時分の最大を取り、その断面の子を読む。
    複勝・ワイドは最低オッズ。無投票・取消の組は返さない。列は ``combo``（馬番か組番。2桁ずつ）・``odds``（倍）。
    締め切り前のオッズが無ければ空の表。表が無い DB では、ほかのリポジトリと同じく空の関係で代わりにする。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, ticket_type: TicketType) -> None:
        self._con = con
        self._ticket_type = ticket_type

    def read(self, race_id: str) -> pd.DataFrame:
        spec = self._ticket_type.spec
        odds_column = "最低オッズ" if spec.has_odds_range else "オッズ"
        parent = facts.optional_relation(self._con, spec.odds_parent, (*keys.RACE_KEY, "データ区分", _ANNOUNCED))
        child = facts.optional_relation(self._con, spec.odds_table, (*keys.RACE_KEY, _ANNOUNCED, spec.combo_column, odds_column))
        announced_at = keys.q(_ANNOUNCED)
        sql = f"""
        WITH latest AS (
            SELECT h.{announced_at} AS announced_at
            FROM {parent} AS h
            WHERE {keys.rid_expr('h')} = ?
              AND h.{keys.q('データ区分')} IN {keys.sql_list(_BEFORE_FINAL_STAGES)}
            ORDER BY announced_at DESC LIMIT 1
        )
        SELECT trim(o.{keys.q(spec.combo_column)}) AS {COMBO},
               NULLIF(TRY_CAST(o.{keys.q(odds_column)} AS INTEGER), 0) / {_ODDS_SCALE} AS {ODDS}
        FROM {child} AS o, latest
        WHERE {keys.rid_expr('o')} = ?
          AND o.{announced_at} = latest.announced_at
          AND NULLIF(TRY_CAST(o.{keys.q(odds_column)} AS INTEGER), 0) IS NOT NULL
        ORDER BY {COMBO}
        """
        return self._con.execute(sql, [race_id, race_id]).df()
