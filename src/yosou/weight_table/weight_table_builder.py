"""出走の表から、馬体重の表 W を作る。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import names
from .weight_table import WeightTable

#: マスの差を、同じ増減の帯の全体の差に寄せる重み（出走数）。
POOL_WEIGHT = 300


class WeightTableBuilder:
    """``WeightRuns`` の表から、帯3つ（増減 × 間隔 × 馬齢）ごとの「実際の3着以内率 − 市場から見た3着以内率」の平均を出し、
    件数の少ないマスは同じ増減の帯の全体の値に寄せる（設計書「買うレースと買い目を決める」06 の 2）。

    縮めた差 = （件数 × マスの差 + 300 × 増減の帯の差）÷（件数 + 300）。
    市場は発表された馬体重を見てオッズを動かすので、差は「市場が割り引き足りない分」になる。
    ``before`` を渡すと、その日より前のレースだけで作る（学習データの材料にするときのリーク防止。年ごとに作り直す）。
    """

    def build(self, prepared: pd.DataFrame, before: date | None = None) -> WeightTable:
        rows = prepared if before is None else prepared[prepared["race_date"] < pd.Timestamp(before)]
        rows = rows.dropna(subset=[names.TOP3, names.MARKET_TOP3, *names.BANDS])
        gap = rows[names.TOP3] - rows[names.MARKET_TOP3]
        table = rows.assign(_gap=gap).groupby(list(names.BANDS), sort=True)["_gap"].agg(["count", "mean"]).reset_index()
        table = table.rename(columns={"count": names.COUNT, "mean": names.RAW_GAP})
        by_change = rows.assign(_gap=gap).groupby(names.CHANGE_BAND, sort=True)["_gap"].mean()
        table[names.BAND_GAP] = table[names.CHANGE_BAND].map(by_change).astype("float64")
        count = table[names.COUNT].to_numpy(dtype="float64")
        table[names.GAP] = (count * table[names.RAW_GAP].to_numpy() + POOL_WEIGHT * table[names.BAND_GAP].to_numpy()) / (count + POOL_WEIGHT)
        as_of = None if rows.empty else rows["race_date"].max().date()
        return WeightTable(table, as_of)
