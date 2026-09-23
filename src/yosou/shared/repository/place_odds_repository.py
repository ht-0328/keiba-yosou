"""複勝オッズ（最低・最高）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from .target_scope import TargetScope

#: オッズ1（単複枠）の親の表と、馬番ごとの複勝オッズが入る子の表。
_HEADER_TABLE = "o1"
_ODDS_TABLE = "o1__複勝オッズ"
_ANNOUNCED = "発表月日時分"
_HEADER_COLUMNS = (*keys.RACE_KEY, "データ区分", _ANNOUNCED)
_ODDS_COLUMNS = (*keys.RACE_KEY, _ANNOUNCED, "馬番", "最低オッズ", "最高オッズ")
#: 使う断面のデータ区分（1 中間・2 前日売最終・3 最終・4 確定・5 確定(月曜)）。9 中止は使わない。
_STAGES: tuple[str, ...] = ("1", "2", "3", "4", "5")
#: 確定の断面（4・5）。あればこれを使い、無ければ締め切り前のいちばん新しい断面を使う。
_FINAL_STAGES: tuple[str, ...] = ("4", "5")
#: オッズは10倍の整数で入っている（``'0023'`` = 2.3倍）。0 は無投票、``----``・``****`` は取消（数にできない）。
_ODDS_SCALE = 10.0


class PlaceOddsRepository:
    """対象の出走のレースの、馬番ごとの複勝オッズ（最低・最高）を読む（既存モデルの修正計画の 2「3着以内と複勝的中」）。

    複勝の払戻は、3着以内に入った馬の組み合わせで変わるので、買う時点では最低〜最高の幅しか分からない。
    終わったレースは確定の断面（4・5）を、これから走るレースは締め切り前のいちばん新しい断面を使う。
    表が無い DB（合成DB など）では、同じ列を持つ空の関係で代わりにする。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """1行 = 1頭。列は ``race_id``・``horse_no``・``place_odds_low``・``place_odds_high``（倍）。"""
        header = facts.optional_relation(self._con, _HEADER_TABLE, _HEADER_COLUMNS)
        child = facts.optional_relation(self._con, _ODDS_TABLE, _ODDS_COLUMNS)
        join = " AND ".join(f"{keys.col(name, 'o')} = {keys.col(name, 'h')}" for name in (*keys.RACE_KEY, _ANNOUNCED))
        is_final = f"{keys.col('データ区分', 'h')} IN {keys.sql_list(_FINAL_STAGES)}"
        sql = f"""
        WITH wanted AS (
            SELECT DISTINCT race_id FROM {scope.relation}
        ), latest AS (
            SELECT {keys.key_list('h')}, {keys.col(_ANNOUNCED, 'h')}, {keys.rid_expr('h')} AS race_id
            FROM {header} AS h
            WHERE {keys.rid_expr('h')} IN (SELECT race_id FROM wanted)
              AND {keys.col('データ区分', 'h')} IN {keys.sql_list(_STAGES)}
            QUALIFY row_number() OVER (
                PARTITION BY {keys.key_list('h')} ORDER BY ({is_final}) DESC, {keys.col(_ANNOUNCED, 'h')} DESC
            ) = 1
        )
        SELECT h.race_id, TRY_CAST({keys.col('馬番', 'o')} AS INTEGER) AS horse_no,
               NULLIF(TRY_CAST({keys.col('最低オッズ', 'o')} AS INTEGER), 0) / {_ODDS_SCALE} AS place_odds_low,
               NULLIF(TRY_CAST({keys.col('最高オッズ', 'o')} AS INTEGER), 0) / {_ODDS_SCALE} AS place_odds_high
        FROM {child} AS o
        JOIN latest AS h ON {join}
        WHERE TRY_CAST({keys.col('馬番', 'o')} AS INTEGER) IS NOT NULL
        """
        return self._con.execute(sql).df()
