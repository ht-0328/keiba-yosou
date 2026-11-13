"""ある日より前の WIN5 の回ごとの当たり組・払戻・発売票数などを読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通 import facts, keys

from .win5_columns import (
    CARRY,
    COMBO,
    COMBO_SEQ,
    HIT_VOTES,
    INVERSE_SUMS,
    NO_HIT,
    PAYOUT,
    RACE_DATE,
    RACE_IDS,
    REFUNDED,
    SATURDAY,
    VOTES,
    WINNER_ODDS,
)

_DAY_TABLE = "wf"
_RACE_TABLE = "wf__重勝式対象レース情報"
_PAYOUT_TABLE = "wf__重勝式払戻情報"
_DAY_COLUMNS = (
    "開催年", "開催月日", "データ区分", "重勝式発売票数", "返還フラグ", "的中無フラグ", "キャリーオーバー金額初期",
)
_RACE_COLUMNS = ("開催年", "開催月日", "_連番", *keys.RACE_KEY[2:])
_PAYOUT_COLUMNS = ("開催年", "開催月日", "_連番", "組番", "重勝式払戻金", "的中票数")
#: 払戻の確定した成績の版（月曜）。中止（9）と速報の版（1〜3）は読まない。
_RESULT_STAGE = "7"
#: 組番の長さ（5頭 × 2桁）。払戻の子表の空きの行を除く。
_COMBO_LENGTH = 10
#: 単勝オッズは10倍の整数の文字列。
_ODDS_SCALE = 10.0
#: DuckDB の ``dayofweek`` の土曜。
_SATURDAY = 6


class Win5HistoryRepository:
    """元DB の ``wf``・``wf__重勝式対象レース情報``・``wf__重勝式払戻情報`` と ``se`` から、ある日より前の WIN5 を読む（SQL 1本）。

    1行 = 1回の当たり組（同着で当たり組が2つあれば2行）。列は開催日・土曜か・発売票数・キャリーオーバー金額初期・返還と的中無の印・
    当たり組の連番と組番・100円あたりの払戻・的中票数と、対象レース5つのレースID・当たり組の5頭の確定単勝オッズ・
    各対象レースの全頭の単勝オッズの逆数の合計（どれも発売の順のリスト。市場の組の確率の元）。
    成績の版（データ区分 7）だけを読み、中止の回は読まない。的中無の回も行を返す（発売票数の見積もりに使う。払戻は 0）。
    単勝オッズは ``se`` のいちばん新しい行（確定オッズ）から読む（事実表を作らないので速い）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, before: date) -> pd.DataFrame:
        """``before`` より前の WIN5 の回ごとの当たり組。開催日と当たり組の連番の順。"""
        frame = self._con.execute(self._sql(), [before.strftime("%Y%m%d")]).df()
        frame[RACE_IDS] = frame[RACE_IDS].map(list)
        frame[WINNER_ODDS] = frame[WINNER_ODDS].map(list)
        frame[INVERSE_SUMS] = frame[INVERSE_SUMS].map(list)
        return frame

    def _sql(self) -> str:
        day_table = facts.optional_relation(self._con, _DAY_TABLE, _DAY_COLUMNS)
        race_table = facts.optional_relation(self._con, _RACE_TABLE, _RACE_COLUMNS)
        payout_table = facts.optional_relation(self._con, _PAYOUT_TABLE, _PAYOUT_COLUMNS)
        year, mmdd = keys.q("開催年"), keys.q("開催月日")
        race_id = " || ".join(keys.col(name, "t") for name in keys.RACE_KEY)
        odds = f"TRY_CAST(NULLIF({keys.q('単勝オッズ')}, '{keys.NO_ODDS}') AS INTEGER) / {_ODDS_SCALE}"
        return f"""
        WITH days AS (
            SELECT {year}, {mmdd}, {keys.race_date_expr()} AS race_date,
                   TRY_CAST({keys.q('重勝式発売票数')} AS BIGINT) AS votes,
                   COALESCE(TRY_CAST({keys.q('キャリーオーバー金額初期')} AS BIGINT), 0) AS carry,
                   {keys.q('返還フラグ')} = '1' AS refunded, {keys.q('的中無フラグ')} = '1' AS no_hit
            FROM {day_table}
            WHERE {keys.q('データ区分')} = '{_RESULT_STAGE}' AND {year} || {mmdd} < ?
        ),
        legs AS (
            SELECT t.{year}, t.{mmdd}, TRY_CAST(t.{keys.q('_連番')} AS INTEGER) AS leg, {race_id} AS rid
            FROM {race_table} AS t
            JOIN days USING ({year}, {mmdd})
        ),
        runners AS (
            SELECT {keys.rid_expr()} AS rid, TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no, {odds} AS odds
            FROM se
            WHERE {keys.rid_expr()} IN (SELECT rid FROM legs)
            {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        ),
        sums AS (
            SELECT rid, sum(1.0 / odds) FILTER (odds > 0) AS inverse_sum FROM runners GROUP BY rid
        ),
        combos AS (
            SELECT {year}, {mmdd}, TRY_CAST({keys.q('_連番')} AS INTEGER) AS combo_seq, trim({keys.q('組番')}) AS combo,
                   COALESCE(TRY_CAST({keys.q('重勝式払戻金')} AS BIGINT), 0) AS payout,
                   COALESCE(TRY_CAST({keys.q('的中票数')} AS BIGINT), 0) AS hit_votes
            FROM {payout_table}
            WHERE length(trim({keys.q('組番')})) = {_COMBO_LENGTH}
        )
        SELECT d.race_date AS {keys.q(RACE_DATE)},
               dayofweek(CAST(d.race_date AS DATE)) = {_SATURDAY} AS {keys.q(SATURDAY)},
               d.votes AS {keys.q(VOTES)}, d.carry AS {keys.q(CARRY)},
               d.refunded AS {keys.q(REFUNDED)}, d.no_hit AS {keys.q(NO_HIT)},
               c.combo_seq AS {keys.q(COMBO_SEQ)}, c.combo AS {keys.q(COMBO)},
               c.payout AS {keys.q(PAYOUT)}, c.hit_votes AS {keys.q(HIT_VOTES)},
               list(l.rid ORDER BY l.leg) AS {keys.q(RACE_IDS)},
               list(r.odds ORDER BY l.leg) AS {keys.q(WINNER_ODDS)},
               list(s.inverse_sum ORDER BY l.leg) AS {keys.q(INVERSE_SUMS)}
        FROM days AS d
        JOIN combos AS c USING ({year}, {mmdd})
        JOIN legs AS l USING ({year}, {mmdd})
        LEFT JOIN runners AS r ON r.rid = l.rid AND r.horse_no = TRY_CAST(substr(c.combo, 2 * l.leg - 1, 2) AS INTEGER)
        LEFT JOIN sums AS s ON s.rid = l.rid
        GROUP BY ALL
        ORDER BY d.race_date, c.combo_seq
        """
