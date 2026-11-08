"""ある日より前の WIN5 の対象レースの出走馬と、レースの発走時刻・障害かを読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import codes, facts, keys

from .win5_columns import HORSE_NO, JUMP, LEG, POST_TIME, RACE_DATE, RACE_ID, WIN_ODDS

_DAY_TABLE = "wf"
_RACE_TABLE = "wf__重勝式対象レース情報"
_DAY_COLUMNS = ("開催年", "開催月日", "データ区分")
_RACE_COLUMNS = ("開催年", "開催月日", "_連番", *keys.RACE_KEY[2:])
#: 払戻の確定した成績の版（月曜）。
_RESULT_STAGE = "7"
#: 単勝オッズは10倍の整数の文字列。
_ODDS_SCALE = 10.0
#: 障害の芝ダの名前（``codes.surface_sql`` の値）。
_JUMP_SURFACE = "障害"


class Win5LegRunnerHistoryRepository:
    """元DB の ``wf``・``wf__重勝式対象レース情報`` と ``ra``・``se`` から、ある日より前の WIN5（成績の版）の対象レースの出走馬を読む（SQL 1本）。

    1行 = 対象レースの1頭（出走取消・発走除外・競走除外を除く）。列は開催日・何レース目・レースID・障害か・発走時刻（``HHMM``）・馬番・
    確定の単勝オッズ（倍。無ければ欠損値）。``ra``・``se`` はいちばん新しい行（成績）を読む。
    過去の WIN5 での確かめ（道具「印の成績」の ``--win5``）が、区切りごとの予測と合わせて対象レースの確率の表を作り（障害のレースは
    オッズから見た勝率で代える）、1レース目からの発走の間隔で馬体重が出ていたかをまねるのに使う（設計書 07 の「過去のレースで確かめるときの時点のまね方」）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, before: date) -> pd.DataFrame:
        """``before`` より前の WIN5 の対象レースの出走馬。開催日・何レース目・馬番の順。"""
        return self._con.execute(self._sql(), [before.strftime("%Y%m%d")]).df()

    def _sql(self) -> str:
        day_table = facts.optional_relation(self._con, _DAY_TABLE, _DAY_COLUMNS)
        race_table = facts.optional_relation(self._con, _RACE_TABLE, _RACE_COLUMNS)
        year, mmdd = keys.q("開催年"), keys.q("開催月日")
        race_id = " || ".join(keys.col(name, "t") for name in keys.RACE_KEY)
        odds = f"TRY_CAST(NULLIF({keys.q('単勝オッズ')}, '{keys.NO_ODDS}') AS INTEGER) / {_ODDS_SCALE}"
        return f"""
        WITH legs AS (
            SELECT {keys.race_date_expr('t')} AS race_date, TRY_CAST(t.{keys.q('_連番')} AS INTEGER) AS leg, {race_id} AS rid
            FROM {race_table} AS t
            JOIN {day_table} AS w USING ({year}, {mmdd})
            WHERE w.{keys.q('データ区分')} = '{_RESULT_STAGE}' AND w.{year} || w.{mmdd} < ?
        ),
        races AS (
            SELECT {keys.rid_expr()} AS rid, {codes.surface_sql(keys.q('トラックコード'))} = '{_JUMP_SURFACE}' AS jump,
                   trim({keys.q('発走時刻')}) AS post_time
            FROM ra
            WHERE {keys.rid_expr()} IN (SELECT rid FROM legs)
            {keys.latest_qualify(keys.RACE_KEY)}
        ),
        runners AS (
            SELECT {keys.rid_expr()} AS rid, TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no, {odds} AS odds,
                   {keys.q('異常区分コード')} AS abnormal
            FROM se
            WHERE {keys.rid_expr()} IN (SELECT rid FROM legs)
            {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        )
        SELECT l.race_date AS {keys.q(RACE_DATE)}, l.leg AS {keys.q(LEG)}, l.rid AS {keys.q(RACE_ID)},
               COALESCE(r.jump, false) AS {keys.q(JUMP)}, r.post_time AS {keys.q(POST_TIME)},
               s.horse_no AS {keys.q(HORSE_NO)}, s.odds AS {keys.q(WIN_ODDS)}
        FROM legs AS l
        LEFT JOIN races AS r ON r.rid = l.rid
        JOIN runners AS s ON s.rid = l.rid
        WHERE s.horse_no > 0 AND s.abnormal NOT IN {keys.sql_list(keys.NOT_RAN_CODES)}
        ORDER BY l.race_date, l.leg, s.horse_no
        """
