"""競走馬の市場取引価格（セリでいくらで売れたか）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import facts, keys

_HS_COLUMNS = (keys.HORSE_KEY, "市場の開催期間(終了日)", "取引価格", "取引時の競走馬の年齢")


class SalePriceRepository:
    """JV-Data の「競走馬市場取引価格」（hs）の、価格の付いた取引を全部読む（1 SQL）。表が無い DB では空の表。

    1頭が何度かセリに出ることがあるので、1行 = 1回の取引。どの取引を使うかは、特徴量を作る側
    （``SalePriceColumns``）が決める。研究「一番人気を疑う」で足した材料。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> pd.DataFrame:
        """列は ``horse_id``・``sale_end``（セリの終わりの日）・``price``（円）・``sale_age``（取引のときの年齢）。"""
        hs = facts.optional_relation(self._con, "hs", _HS_COLUMNS)
        sql = f"""
        SELECT {keys.q(keys.HORSE_KEY)} AS horse_id,
               try_strptime("市場の開催期間(終了日)", '%Y%m%d')::date AS sale_end,
               try_cast("取引価格" AS BIGINT) AS price,
               try_cast("取引時の競走馬の年齢" AS INTEGER) AS sale_age
        FROM {hs}
        WHERE try_cast("取引価格" AS BIGINT) > 0
        """
        frame = self._con.execute(sql).df()
        return frame.assign(sale_end=pd.to_datetime(frame["sale_end"]))
