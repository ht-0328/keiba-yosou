"""セリの取引価格の列を足す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 足す列。
NAMES: tuple[str, ...] = ("セリの価格（log）", "セリで買われた", "セリの時の年齢", "セリの価格のレース内順位",
                          "セリの価格とレースの最高との差")


class SalePriceFeatures:
    """馬ごとのセリの取引価格から、その出走の時点で分かる値を足す。

    使うのは、レースの日より前に終わったセリのうち、いちばん新しいもの。セリで買われていない馬（生産者がそのまま
    持つ馬など）は、価格を欠損にし、「セリで買われた」を 0 にする。
    ``frame`` は ``horse_id``・``開催日``・``レースID`` の列を持つ1行 = 1頭の表、``sales`` は
    ``SalePriceRepository`` が読んだ表（``horse_id``・``sale_end``・``price``・``sale_age``）。
    """

    def add(self, frame: pd.DataFrame, sales: pd.DataFrame) -> list[str]:
        rows = frame[["horse_id", "開催日"]].reset_index().merge(sales, on="horse_id", how="left")
        rows = rows[rows["sale_end"].notna() & (rows["sale_end"] < rows["開催日"])]
        latest = rows.sort_values("sale_end").drop_duplicates("index", keep="last").set_index("index")
        price = np.log10(latest["price"].reindex(frame.index))
        frame["セリの価格（log）"] = price
        frame["セリで買われた"] = price.notna().astype(int)
        frame["セリの時の年齢"] = latest["sale_age"].reindex(frame.index)
        by_race = price.groupby(frame["レースID"])
        frame["セリの価格のレース内順位"] = by_race.rank(ascending=False, pct=True)
        frame["セリの価格とレースの最高との差"] = price - by_race.transform("max")
        return list(NAMES)
