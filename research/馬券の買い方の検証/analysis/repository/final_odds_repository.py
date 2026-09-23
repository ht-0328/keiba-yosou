"""1つの券種の確定オッズを、期間ぶん読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from ..ticket import TicketType
from .race_day_range import RaceDayRange

#: 確定オッズのデータ区分（4 確定・5 確定(月曜)）。締め切り前（1〜3）と中止（9）は読まない。
_FINAL_STAGES: tuple[str, ...] = ("4", "5")
#: オッズは10倍の整数で入っている（``'000123'`` = 12.3倍）。0 は無投票、``----``・``****`` は取消（数値にできない）。
_ODDS_SCALE = 10.0
_ANNOUNCED = "発表月日時分"
#: 出力の列（オッズが1つの券種）。複勝・ワイドは ``odds_high`` が足される。
ODDS, ODDS_HIGH, POPULARITY, COMBO = "odds", "odds_high", "popularity", "combo"


class FinalOddsRepository:
    """1つの券種の確定オッズを、期間の全レースぶん 1組番1行で読む（``o1``〜``o6``）。

    子の表にはデータ区分が無いので、親をデータ区分 4・5 に絞って1レース1行にし、その発表月日時分で子と結ぶ
    （5 の発表月日時分は ``'00000000'`` なので、最大を取ると壊れる）。無投票・取消の行は落とす。
    列は ``race_id``・``combo``（馬番か組番。2桁ずつ）・``odds``（倍。複勝・ワイドは最低）・``odds_high``（複勝・ワイドだけ。最高）・``popularity``。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, ticket_type: TicketType) -> None:
        self._con = con
        self._ticket_type = ticket_type

    def read(self, days: RaceDayRange) -> pd.DataFrame:
        spec = self._ticket_type.spec
        odds_columns = ("最低オッズ", "最高オッズ") if spec.has_odds_range else ("オッズ",)
        aliases = (ODDS, ODDS_HIGH)[:len(odds_columns)]
        parent = facts.optional_relation(self._con, spec.odds_parent, (*keys.RACE_KEY, "データ区分", "データ作成年月日", _ANNOUNCED))
        child = facts.optional_relation(
            self._con, spec.odds_table, (*keys.RACE_KEY, _ANNOUNCED, "_連番", spec.combo_column, *odds_columns, "人気順"),
        )
        join = " AND ".join(f"{keys.col(column, 'o')} = {keys.col(column, 'h')}" for column in (*keys.RACE_KEY, _ANNOUNCED))
        decoded = ", ".join(
            f"NULLIF(TRY_CAST({keys.col(column, 'o')} AS INTEGER), 0) / {_ODDS_SCALE} AS {alias}"
            for column, alias in zip(odds_columns, aliases)
        )
        sql = f"""
        WITH final_header AS (
            SELECT {keys.key_list('h')}, {keys.col(_ANNOUNCED, 'h')}
            FROM {parent} AS h
            WHERE {keys.col('データ区分', 'h')} IN {keys.sql_list(_FINAL_STAGES)} AND {keys.jra_only('h')} AND {days.condition('h')}
            {keys.latest_qualify(keys.RACE_KEY, 'h')}
        ), odds AS (
            SELECT {keys.rid_expr('o')} AS race_id, trim({keys.col(spec.combo_column, 'o')}) AS {COMBO}, {decoded},
                   TRY_CAST({keys.col('人気順', 'o')} AS INTEGER) AS {POPULARITY}
            FROM {child} AS o
            JOIN final_header AS h ON {join}
        )
        SELECT race_id, {COMBO}, {", ".join(aliases)}, {POPULARITY}
        FROM odds
        WHERE {ODDS} IS NOT NULL
        ORDER BY race_id, {COMBO}
        """
        return self._con.execute(sql, days.params).df()
