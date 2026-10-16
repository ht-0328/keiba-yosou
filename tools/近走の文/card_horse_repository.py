"""出馬表の出走馬を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys

COLUMNS: tuple[str, ...] = ("horse_id", "horse_name", "horse_no")


class CardHorseRepository:
    """1レースの出走馬（血統登録番号・馬名・馬番）を生の表 ``se`` から読む（1 SQL）。

    確定前（出走馬名表・出馬表）でも読める。同じ馬に複数のデータ区分の行があれば最新の1行を使い、出走取消・除外は除く。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, rid: str) -> pd.DataFrame:
        """列は ``COLUMNS``。馬番の順。レースが無ければ空。"""
        condition, params = keys.rid_condition(rid)
        not_ran = keys.sql_list(keys.NOT_RAN_CODES)
        sql = f"""
        WITH latest AS (
            SELECT {keys.q(keys.HORSE_KEY)} AS horse_id, trim("馬名") AS horse_name, TRY_CAST("馬番" AS INTEGER) AS horse_no,
                   "異常区分コード" AS abnormal
            FROM se WHERE {condition} {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
        )
        SELECT horse_id, horse_name, horse_no FROM latest
        WHERE coalesce(abnormal, '0') NOT IN {not_ran}
        ORDER BY horse_no, horse_id
        """
        frame = self._con.execute(sql, params).df()
        return frame.assign(horse_id=frame["horse_id"].astype(str))
