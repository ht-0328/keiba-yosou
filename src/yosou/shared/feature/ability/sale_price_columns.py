"""セリの取引価格から、その出走の時点で分かる列を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class SalePriceColumns:
    """馬ごとのセリの取引価格から、``SALE_COLUMNS`` の5個（ability_columns.py）を作る。

    使うのは、レースの日より前に終わったセリのうち、いちばん新しいもの。セリで買われていない馬（生産者がそのまま
    持つ馬など）は、価格を欠損値にし、「セリで買われた」を 0 にする。価格は log10 にする（1000万円なら 7）。
    ``table`` は race_id・horse_id・race_date を持つ行、``sales`` は ``SalePriceRepository`` が読んだ表。
    """

    def build(self, table: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``table`` と同じ。"""
        rows = table[["horse_id", "race_date"]].reset_index(names="row").merge(sales, on="horse_id", how="inner")
        rows = rows[rows["sale_end"].notna() & (rows["sale_end"] < rows["race_date"])]
        latest = rows.sort_values("sale_end").drop_duplicates("row", keep="last").set_index("row")
        price = np.log10(latest["price"].astype(float)).reindex(table.index)
        by_race = price.groupby(table["race_id"])
        return pd.DataFrame({
            "セリの価格（log）": price, "セリで買われた": price.notna().astype(float),
            "セリの時の年齢": latest["sale_age"].astype(float).reindex(table.index),
            "セリの価格のレース内順位": by_race.rank(ascending=False, pct=True),
            "セリの価格とレースの最高との差": price - by_race.transform("max"),
        }, index=table.index)
