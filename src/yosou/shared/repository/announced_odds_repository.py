"""締め切り前の単勝オッズを読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

#: オッズ1（単複枠）の親の表と、馬番ごとの単勝オッズが入る子の表。
_HEADER_TABLE = "o1"
_ODDS_TABLE = "o1__単勝オッズ"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", "発表月日時分")
_ODDS_COLUMNS = (*keys.RACE_KEY, "発表月日時分", "馬番", "オッズ")
#: 確定前の断面のデータ区分（1 中間・2 前日売最終・3 最終）。4 確定・5 確定(月曜)・9 中止は、予測に使わない。
_BEFORE_FINAL_STAGES: tuple[str, ...] = ("1", "2", "3")
#: 単勝オッズの「無投票」。オッズは 10倍した4桁の文字列で入っている（発売前取消は ----、発売後取消は ****）。
_NO_ODDS = "0000"
_ODDS_SCALE = 10.0


class AnnouncedOddsRepository:
    """締め切り前の単勝オッズ（時系列オッズ）から、1レースのいちばん新しい断面を読む。

    人気を使う予想（``favorites_out_of_top3``・``longshots_in_top3``）が、前日・当日の人気を作るのに使う。
    断面は ``発表月日時分`` で見分ける。この列は JV-Data の仕様で中間オッズにだけ入るので、前日売最終・最終の
    断面は、それを入れて取り込んだ DB でしか引けない。今の元DB には中間の断面がごく少数しか入っておらず、
    ほとんどのレースで行なしになる。取り込みを増やすのは jvdata-store 側の作業である。
    表が無い DB では、ほかのリポジトリと同じく空の関係で代わりにする。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """列は ``horse_no``・``odds``（倍）。締め切り前のオッズが無ければ空の表。"""
        header_table = facts.optional_relation(self._con, _HEADER_TABLE, _HEADER_COLUMNS)
        odds_table = facts.optional_relation(self._con, _ODDS_TABLE, _ODDS_COLUMNS)
        announced_at = keys.q("発表月日時分")
        odds_value = f"TRY_CAST(NULLIF(o.{keys.q('オッズ')}, '{_NO_ODDS}') AS INTEGER)"
        sql = f"""
        WITH latest AS (
            SELECT h.{announced_at} AS announced_at
            FROM {header_table} AS h
            WHERE {keys.rid_expr('h')} = ?
              AND h.{keys.q('データ区分')} IN {keys.sql_list(_BEFORE_FINAL_STAGES)}
            ORDER BY announced_at DESC LIMIT 1
        )
        SELECT TRY_CAST(o.{keys.q('馬番')} AS INTEGER) AS horse_no,
               {odds_value} / {_ODDS_SCALE} AS odds
        FROM {odds_table} AS o, latest
        WHERE {keys.rid_expr('o')} = ?
          AND o.{announced_at} = latest.announced_at
          AND {odds_value} IS NOT NULL
        ORDER BY horse_no
        """
        return self._con.execute(sql, [race_id, race_id]).df()
