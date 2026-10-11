"""表 G（脚質 × ペース × 競馬場と芝ダ ごとの、市場の見立てとの差）の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import names

#: 競馬場と芝ダの鍵。
COURSE_KEY: list[str] = [names.VENUE_CODE, names.SURFACE]


def cell(style: str, pace: str) -> str:
    """脚質とペースのマスの名前（横に並べた表の列。例 ``逃げ|スロー``）。"""
    return f"{style}|{pace}"


CELLS: tuple[str, ...] = tuple(cell(style, pace) for style in names.STYLES for pace in names.PACES)


@dataclass(frozen=True)
class AdvantageTable:
    """表 G。``frame`` は 1行 = 1マス（脚質・ペース・競馬場コード・芝ダ・件数・差・全競馬場の差・縮めた差）で、
    材料にあった競馬場と芝ダの全部の組について 4 × 3 のマスがそろっている。``pool`` は競馬場で分けない
    脚質 × ペース の 12行（材料に無い競馬場に使う）。``as_of`` は材料の最後の開催日（無ければ None）。
    値は3着以内の確率のポイント（+0.02 は、市場の見立てより 2ポイント来やすい）。
    """

    frame: pd.DataFrame
    pool: pd.DataFrame
    as_of: pd.Timestamp | None = None

    def matrix(self, venue_code: str, surface: str) -> pd.DataFrame:
        """その競馬場と芝ダの 4 × 3 の表（行が脚質、列がペース。値は縮めた差）。材料に無ければ全競馬場の値。"""
        rows = self.frame[(self.frame[names.VENUE_CODE] == venue_code) & (self.frame[names.SURFACE] == surface)]
        source = rows if len(rows) else self.pool
        return source.pivot(index=names.STYLE, columns=names.PACE, values=names.GAP).reindex(
            index=list(names.STYLES), columns=list(names.PACES))

    def cells_for(self, venue_codes: pd.Series, surfaces: pd.Series) -> pd.DataFrame:
        """行ごとの競馬場と芝ダに対する 12 のマスの値（列は ``CELLS``）。index は ``venue_codes`` と同じ。材料に無い競馬場は全競馬場の値。"""
        keys = pd.DataFrame({names.VENUE_CODE: venue_codes.astype(str).to_numpy(), names.SURFACE: surfaces.astype(str).to_numpy()})
        wide = keys.merge(self._wide(), on=COURSE_KEY, how="left")[list(CELLS)]
        fallback = self._pool_cells()
        return wide.fillna(fallback).set_axis(venue_codes.index)

    def _wide(self) -> pd.DataFrame:
        """競馬場と芝ダごとに 12 のマスを横に並べた表。"""
        named = self.frame.assign(_cell=[cell(style, pace) for style, pace in zip(self.frame[names.STYLE], self.frame[names.PACE])])
        return named.pivot_table(index=COURSE_KEY, columns="_cell", values=names.GAP, aggfunc="first").reindex(
            columns=list(CELLS)).reset_index()

    def _pool_cells(self) -> pd.Series:
        return pd.Series({cell(style, pace): value for style, pace, value in
                          zip(self.pool[names.STYLE], self.pool[names.PACE], self.pool[names.GAP])}).reindex(list(CELLS))
