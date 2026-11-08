"""1レースの出走馬の馬番・馬名と、出走の行の単勝オッズを読む（障害の対象レースで使う）。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys

#: 列の名前。
HORSE_NO = "馬番"
HORSE_NAME = "馬名"
ODDS = "単勝オッズ"
#: 単勝オッズは10倍の整数の文字列。
_ODDS_SCALE = 10.0


class LegRunnerRepository:
    """``se`` のいちばん新しい行から、1レースの出走馬（出走取消・発走除外・競走除外を除く）の馬番・馬名・単勝オッズを読む（SQL 1本）。

    今のモデルは障害を予想しないので、障害の対象レースはオッズから見た勝率をそのまま1着の確率にする（設計書 15 の 3）。
    そのときの馬の並びに使う。単勝オッズは、終わったレースなら確定オッズ、これからのレースなら空（締め切り前のオッズは
    ``AnnouncedOddsRepository`` が読む）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """列は馬番・馬名・単勝オッズ（倍。無ければ欠損値）。馬番の順。"""
        condition, params = keys.rid_condition(race_id)
        odds = f"TRY_CAST(NULLIF({keys.q('単勝オッズ')}, '{keys.NO_ODDS}') AS INTEGER) / {_ODDS_SCALE}"
        sql = f"""
        WITH latest AS (
            SELECT TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no, {keys.q('馬名')} AS horse_name, {odds} AS odds,
                   {keys.q('異常区分コード')} AS abnormal
            FROM se
            WHERE {condition}
            {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        )
        SELECT horse_no AS {keys.q(HORSE_NO)}, trim(horse_name) AS {keys.q(HORSE_NAME)}, odds AS {keys.q(ODDS)}
        FROM latest
        WHERE horse_no > 0 AND abnormal NOT IN {keys.sql_list(keys.NOT_RAN_CODES)}
        ORDER BY horse_no
        """
        return self._con.execute(sql, params).df()
