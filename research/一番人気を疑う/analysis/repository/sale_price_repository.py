"""競走馬の市場取引価格（セリでいくらで売れたか）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

_SQL = """
select 血統登録番号 as horse_id,
    try_strptime("市場の開催期間(終了日)", '%Y%m%d')::date as sale_end,
    try_cast(取引価格 as bigint) as price,
    try_cast(取引時の競走馬の年齢 as integer) as sale_age
from hs
where try_cast(取引価格 as bigint) > 0
"""


class SalePriceRepository:
    """JV-Data の「競走馬市場取引価格」（hs）の、価格の付いた取引を全部読む。

    1頭が何度かセリに出ることがあるので、1行 = 1回の取引。どの取引を使うかは ``SalePriceFeatures`` が決める。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._connection = connection

    def read(self) -> pd.DataFrame:
        """``horse_id``・``sale_end``（セリの終わりの日）・``price``（円）・``sale_age``（取引のときの年齢）。"""
        return self._connection.execute(_SQL).fetch_df()
