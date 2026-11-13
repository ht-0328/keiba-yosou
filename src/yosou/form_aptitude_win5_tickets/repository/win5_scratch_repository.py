"""ある日より前の WIN5 の対象レースの、出走取消・競走除外の馬番を読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys

from .win5_columns import HORSE_NO, LEG, RACE_DATE

_DAY_TABLE = "wf"
_RACE_TABLE = "wf__重勝式対象レース情報"
_DAY_COLUMNS = ("開催年", "開催月日", "データ区分")
_RACE_COLUMNS = ("開催年", "開催月日", "_連番", *keys.RACE_KEY[2:])
_RESULT_STAGE = "7"


class Win5ScratchRepository:
    """元DB の ``wf``・``wf__重勝式対象レース情報`` と ``se`` から、ある日より前の WIN5 の対象レースで、出走取消・発走除外・競走除外
    （異常区分 1〜3）になった馬の馬番を読む（SQL 1本）。1行 = 1頭。

    その馬を含む組は返還になる（代金が戻る）ので、過去の WIN5 での精算（``Win5Settlement``）に使う。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, before: date) -> pd.DataFrame:
        """列は開催日・何レース目・馬番。"""
        return self._con.execute(self._sql(), [before.strftime("%Y%m%d")]).df()

    def _sql(self) -> str:
        day_table = facts.optional_relation(self._con, _DAY_TABLE, _DAY_COLUMNS)
        race_table = facts.optional_relation(self._con, _RACE_TABLE, _RACE_COLUMNS)
        year, mmdd = keys.q("開催年"), keys.q("開催月日")
        race_id = " || ".join(keys.col(name, "t") for name in keys.RACE_KEY)
        return f"""
        WITH legs AS (
            SELECT {keys.race_date_expr('t')} AS race_date, TRY_CAST(t.{keys.q('_連番')} AS INTEGER) AS leg, {race_id} AS rid
            FROM {race_table} AS t
            JOIN {day_table} AS w USING ({year}, {mmdd})
            WHERE w.{keys.q('データ区分')} = '{_RESULT_STAGE}' AND w.{year} || w.{mmdd} < ?
        ),
        runners AS (
            SELECT {keys.rid_expr()} AS rid, TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no,
                   {keys.q('異常区分コード')} AS abnormal
            FROM se
            WHERE {keys.rid_expr()} IN (SELECT rid FROM legs)
            {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        )
        SELECT l.race_date AS {keys.q(RACE_DATE)}, l.leg AS {keys.q(LEG)}, r.horse_no AS {keys.q(HORSE_NO)}
        FROM legs AS l
        JOIN runners AS r ON r.rid = l.rid
        WHERE r.abnormal IN {keys.sql_list(keys.NOT_RAN_CODES)}
        ORDER BY l.race_date, l.leg, r.horse_no
        """
