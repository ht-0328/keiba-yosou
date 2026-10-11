"""材料から表 G を作る。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import names
from .advantage_table import COURSE_KEY, AdvantageTable

#: 縮小推定の重み。マスの件数がこの数と同じなら、そのマスの値と全競馬場の値を半分ずつ混ぜる（初期値）。
PRIOR_WEIGHT = 500
#: 1マスの鍵。
_CELL_KEY: list[str] = [names.STYLE, names.PACE, *COURSE_KEY]
_POOL_KEY: list[str] = [names.STYLE, names.PACE]


class AdvantageTableBuilder:
    """``AdvantageRuns`` の表から、表 G を作る（設計書 05 の 2）。

    マスの値 = そのマスの出走の「3着以内（1 か 0）− 市場から見た3着以内率」の平均。件数の少ないマスが偶然で大きく出ないように、
    同じ脚質 × ペースの全競馬場の値に寄せる（縮めた差 = (件数 × 差 + 重み × 全競馬場の差) ÷ (件数 + 重み)）。
    脚質・ペース・市場の見立て・着順のどれかが無い出走は数えない。``before`` を渡すと、その日より前のレースだけで作る
    （学習データに付けるときのリークを防ぐ。年ごとに前の年までで作り直す）。
    """

    def build(self, prepared: pd.DataFrame, before: date | None = None) -> AdvantageTable:
        rows = prepared.dropna(subset=[names.STYLE, names.PACE, names.MARKET_TOP3, names.TOP3])
        if before is not None:
            rows = rows[rows["race_date"] < pd.Timestamp(before)]
        gap = rows[names.TOP3] - rows[names.MARKET_TOP3]
        keyed = rows[_CELL_KEY].assign(_gap=gap)
        by_cell = keyed.groupby(_CELL_KEY, observed=True)["_gap"].agg(["size", "mean"])
        by_pool = keyed.groupby(_POOL_KEY, observed=True)["_gap"].agg(["size", "mean"])
        pool = self._full_pool(by_pool)
        frame = self._full_cells(by_cell, rows[COURSE_KEY].drop_duplicates(), pool)
        as_of = rows["race_date"].max() if len(rows) else None
        return AdvantageTable(frame, pool, None if pd.isna(as_of) else as_of)

    def _full_pool(self, by_pool: pd.DataFrame) -> pd.DataFrame:
        """脚質 × ペースの 12行（材料に無い組は件数 0・差 0）。"""
        grid = pd.MultiIndex.from_product([list(names.STYLES), list(names.PACES)], names=_POOL_KEY)
        filled = by_pool.reindex(grid)
        return pd.DataFrame({
            names.STYLE: grid.get_level_values(0), names.PACE: grid.get_level_values(1),
            names.COUNT: filled["size"].fillna(0).astype(int).to_numpy(),
            names.GAP: filled["mean"].fillna(0.0).to_numpy(),
        })

    def _full_cells(self, by_cell: pd.DataFrame, courses: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
        """競馬場と芝ダごとに 4 × 3 のマスをそろえ、縮めた差を付けた表。"""
        pool_keyed = pool.set_index(_POOL_KEY)
        grid = pd.MultiIndex.from_tuples(
            [(style, pace, venue, surface) for venue, surface in courses.itertuples(index=False)
             for style in names.STYLES for pace in names.PACES], names=_CELL_KEY)
        filled = by_cell.reindex(grid)
        count = filled["size"].fillna(0).to_numpy()
        raw = filled["mean"].to_numpy()
        pool_gap = pool_keyed[names.GAP].reindex(grid.droplevel(COURSE_KEY)).to_numpy()
        shrunk = (count * pd.Series(raw).fillna(0.0).to_numpy() + PRIOR_WEIGHT * pool_gap) / (count + PRIOR_WEIGHT)
        return pd.DataFrame({
            names.STYLE: grid.get_level_values(0), names.PACE: grid.get_level_values(1),
            names.VENUE_CODE: grid.get_level_values(2), names.SURFACE: grid.get_level_values(3),
            names.COUNT: count.astype(int), names.RAW_GAP: raw, names.POOL_GAP: pool_gap, names.GAP: shrunk,
        })
