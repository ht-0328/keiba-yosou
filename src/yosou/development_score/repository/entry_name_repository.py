"""1レースの出走馬の馬番と馬名を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import keys

#: 出力の列。
HORSE_ID, HORSE_NO, HORSE_NAME = "horse_id", "馬番", "馬名"


class EntryNameRepository:
    """馬毎レース情報（``se``）から、1レースの出走馬の馬ID・馬番・馬名を読む（結果を人が見るためだけ）。

    木曜（出走馬名表）は馬番が未定で欠損値。取消の馬も含む（展開の予想が予測した馬だけを、呼ぶ側が突き合わせる）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """列は ``horse_id``・``馬番``（整数か欠損値）・``馬名``。馬番の順。"""
        cond, params = keys.rid_condition(race_id)
        frame = self._con.execute(
            f"""
            SELECT "血統登録番号" AS horse_id, TRY_CAST("馬番" AS INTEGER) AS "馬番", trim("馬名") AS "馬名"
            FROM se WHERE {cond} {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
            ORDER BY TRY_CAST("馬番" AS INTEGER), trim("馬名")
            """, params,
        ).df()
        return frame.assign(**{HORSE_ID: frame[HORSE_ID].astype(str), HORSE_NO: frame[HORSE_NO].astype("Int64")})
