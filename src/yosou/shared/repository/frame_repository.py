"""出走馬の枠番を、期間ぶん読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

from .race_day_range import RaceDayRange

#: 出力の列。
HORSE_NO, FRAME = "horse_no", "frame"


class FrameRepository:
    """期間の中央のレースの、馬番 → 枠番を 1頭1行で読む（``se``。枠連の組を作るのに使う）。

    データ区分の違う行（出馬表・成績）があっても枠番は変わらないので、1頭1行にまとめる。枠番の決まっていない行（0）は落とす。
    列は ``race_id``・``horse_no``・``frame``。例: 1枠1番・1枠2番・2枠3番 … の 16頭立てなら 16行。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, days: RaceDayRange) -> pd.DataFrame:
        frame_no = f"TRY_CAST({keys.col('枠番', 's')} AS INTEGER)"
        sql = f"""
        SELECT {keys.rid_expr('s')} AS race_id, TRY_CAST({keys.col('馬番', 's')} AS INTEGER) AS {HORSE_NO}, any_value({frame_no}) AS {FRAME}
        FROM se AS s
        WHERE {facts.venue_filter(self._con, 's')} AND {days.condition('s')} AND {frame_no} > 0
        GROUP BY ALL
        """
        return self._con.execute(sql, days.params).df()
