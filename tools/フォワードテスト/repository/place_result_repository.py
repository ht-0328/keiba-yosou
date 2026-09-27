"""記録した買い目のレースの、馬ごとの複勝の払戻と返還を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

#: 払戻が確定した行のデータ区分（1 速報成績（払戻確定）・2 成績（月曜））。
_PAYOUT_STAGES: tuple[str, ...] = ("1", "2")
#: 返還になる異常区分（1 出走取消・2 発走除外）。競走中止・失格は返還されない。
_REFUND_CODES: tuple[str, ...] = ("1", "2")
#: レースが中止になったときの ``ra`` のデータ区分。
_CANCELLED_STAGE = "9"


class PlaceResultRepository:
    """レースの鍵の一覧について、1行 = 1頭で、結果が出たか・複勝の払戻（100円あたり、円）・返還になるかを読む。

    結果が出たかは、払戻の表（``hr``）に確定した行があるかで決める。当日の速報（jvdata-store の ``0B15``）でも
    月曜の成績でも入る。表が無い DB でも落ちないように、無い表は空の関係で代わりにする。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_ids: list[str]) -> pd.DataFrame:
        """列は ``race_id``・``horse_no``・``has_result``・``place_yen``・``refund``。"""
        wanted = f"(SELECT unnest(?::VARCHAR[]))"
        header = facts.optional_relation(self._con, "hr", (*keys.RACE_KEY, "データ区分", "データ作成年月日"))
        place = facts.optional_relation(self._con, "hr__複勝払戻", (*keys.RACE_KEY, "馬番", "払戻金"))
        runner = facts.optional_relation(self._con, "se", (*keys.RACE_KEY, "馬番", "異常区分コード", "データ区分",
                                                          "データ作成年月日"))
        race = facts.optional_relation(self._con, "ra", (*keys.RACE_KEY, "データ区分"))
        sql = f"""
        WITH result AS (
            SELECT DISTINCT {keys.rid_expr()} AS race_id FROM {header}
            WHERE {keys.rid_expr()} IN {wanted} AND {keys.q('データ区分')} IN {keys.sql_list(_PAYOUT_STAGES)}
        ), place AS (
            SELECT {keys.rid_expr()} AS race_id, TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no,
                   max(TRY_CAST({keys.q('払戻金')} AS BIGINT)) AS place_yen
            FROM {place} WHERE {keys.rid_expr()} IN {wanted} GROUP BY ALL
        ), runner AS (
            SELECT {keys.rid_expr()} AS race_id, TRY_CAST({keys.q('馬番')} AS INTEGER) AS horse_no,
                   {keys.q('異常区分コード')} AS abnormal
            FROM {runner} WHERE {keys.rid_expr()} IN {wanted}
            {keys.latest_qualify((*keys.RACE_KEY, '馬番'))}
        ), cancelled AS (
            SELECT DISTINCT {keys.rid_expr()} AS race_id FROM {race}
            WHERE {keys.rid_expr()} IN {wanted} AND {keys.q('データ区分')} = '{_CANCELLED_STAGE}'
        )
        SELECT runner.race_id, runner.horse_no, result.race_id IS NOT NULL AS has_result,
               coalesce(place.place_yen, 0) AS place_yen,
               runner.abnormal IN {keys.sql_list(_REFUND_CODES)} OR cancelled.race_id IS NOT NULL AS refund
        FROM runner
        LEFT JOIN result USING (race_id)
        LEFT JOIN place USING (race_id, horse_no)
        LEFT JOIN cancelled USING (race_id)
        """
        return self._con.execute(sql, [race_ids] * sql.count("?")).df()
