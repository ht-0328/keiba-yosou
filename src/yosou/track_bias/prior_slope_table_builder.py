"""レースごとの傾きから、過去の傾きの表を作る。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import names
from .prior_slope_table import PriorSlopeTable

#: マスの平均を、同じ馬場の全体の平均に寄せる重み（レース数）。件数の少ないマス（例: 開催8日目の不良馬場）が極端な値にならないようにする。
POOL_WEIGHT = 30


class PriorSlopeTableBuilder:
    """``RaceSlopes`` の表（1行 = 1レース）から、``PRIOR_KEY``（同じ馬場 × 開催の何日目 × 馬場状態）ごとの傾きの平均を出し、
    件数の少ないマスは同じ馬場の全体の平均に寄せる（縮小推定）。

    開催の何日目を鍵に入れるのは、開幕週は内の芝が良く、開催の後半ほど内が荒れる、という違いを持たせるため。
    ``before`` を渡すと、その日より前のレースだけで作る（学習データの材料にするときのリーク防止。年ごとに作り直す）。
    縮めた傾き = （件数 × マスの平均 + 30 × 同じ馬場の平均）÷（件数 + 30）。傾きの無いレース（前の傾きが欠損）は、その傾きの平均に数えない。
    """

    def build(self, slopes: pd.DataFrame, before: date | None = None) -> PriorSlopeTable:
        rows = slopes if before is None else slopes[slopes[names.RACE_DATE] < pd.Timestamp(before)]
        courses = self._mean(rows, list(names.COURSE_KEY))
        cells = self._mean(rows, list(names.PRIOR_KEY))
        pooled = cells[list(names.COURSE_KEY)].merge(courses, on=list(names.COURSE_KEY), how="left")
        for slope, prior in ((names.INNER_SLOPE, names.PRIOR_INNER), (names.FRONT_SLOPE, names.PRIOR_FRONT)):
            count = cells[f"{slope}_件数"].to_numpy()
            cells[prior] = (count * cells[prior].to_numpy() + POOL_WEIGHT * pooled[prior].to_numpy()) / (count + POOL_WEIGHT)
        as_of = None if rows.empty else rows[names.RACE_DATE].max().date()
        return PriorSlopeTable(cells[[*names.PRIOR_KEY, names.PRIOR_INNER, names.PRIOR_FRONT]].reset_index(drop=True),
                               courses[[*names.COURSE_KEY, names.PRIOR_INNER, names.PRIOR_FRONT]].reset_index(drop=True), as_of)

    def _mean(self, rows: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """``keys`` ごとの傾きの平均と件数（列 ``PRIOR_INNER``・``PRIOR_FRONT``・``<傾き>_件数``）。平均の無い組は 0 件として 0。"""
        grouped = rows.groupby(keys, sort=False)[[names.INNER_SLOPE, names.FRONT_SLOPE]]
        means = grouped.mean().rename(columns={names.INNER_SLOPE: names.PRIOR_INNER, names.FRONT_SLOPE: names.PRIOR_FRONT})
        counts = grouped.count().rename(columns={slope: f"{slope}_件数" for slope in names.SLOPES})
        return means.fillna(0.0).join(counts).reset_index()
