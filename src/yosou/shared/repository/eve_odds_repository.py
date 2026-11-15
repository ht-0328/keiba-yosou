"""前日の最後の単勝オッズを読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

#: オッズ1（単複枠）の親の表と、馬番ごとの単勝オッズが入る子の表。
_HEADER_TABLE = "o1"
_ODDS_TABLE = "o1__単勝オッズ"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", "発表月日時分")
_ODDS_COLUMNS = (*keys.RACE_KEY, "発表月日時分", "馬番", "オッズ")
#: 途中のオッズ（中間）のデータ区分。
_INTERIM_STAGE = "1"
_ODDS_SCALE = 10.0


class EveOddsRepository:
    """1レースの、開催日より前（前日まで）に発表された最後の途中の単勝オッズ（馬番ごと）を読む。

    当日の予想の確率をオッズの動きで直す（``OddsMoveCorrection``）のに使う。途中のオッズは ``発表月日時分``（月日時分）で見分け、
    その月日が開催月日より前の断面のうち、いちばん新しいものを取る。元DB に途中のオッズが入っているのは 2025年9月6日からで、
    それより前のレースと、前日に発売の無いレースは行なしになる。表が無い DB では空の関係で代わりにする。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """列は ``horse_no``・``eve_odds``（倍）。前日のオッズが無ければ空の表。"""
        header_table = facts.optional_relation(self._con, _HEADER_TABLE, _HEADER_COLUMNS)
        odds_table = facts.optional_relation(self._con, _ODDS_TABLE, _ODDS_COLUMNS)
        announced_at = keys.q("発表月日時分")
        odds_value = f"TRY_CAST(NULLIF(o.{keys.q('オッズ')}, '{keys.NO_ODDS}') AS INTEGER)"
        sql = f"""
        WITH last AS (
            SELECT max(h.{announced_at}) AS announced_at
            FROM {header_table} AS h
            WHERE {keys.rid_expr('h')} = ?
              AND h.{keys.q('データ区分')} = '{_INTERIM_STAGE}'
              AND substr(h.{announced_at}, 1, 4) < h.{keys.q('開催月日')}
        )
        SELECT TRY_CAST(o.{keys.q('馬番')} AS INTEGER) AS horse_no,
               {odds_value} / {_ODDS_SCALE} AS eve_odds
        FROM {odds_table} AS o, last
        WHERE {keys.rid_expr('o')} = ?
          AND o.{announced_at} = last.announced_at
          AND {odds_value} IS NOT NULL
        ORDER BY horse_no
        """
        return self._con.execute(sql, [race_id, race_id]).df()
