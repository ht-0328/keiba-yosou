"""人気薄の1着の予想の学習データ（行を選べる表の束）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

#: ID の列の名前（学習の表と同じ）。
RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO = "レースID", "開催日", "馬ID", "馬番"


@dataclass(frozen=True)
class LongshotData:
    """1行 = 1頭。``ids`` は ID 列、``features`` は特徴量、``label`` は1着なら 1、``baseline`` はオッズから見た勝率のロジット、
    ``popularity`` は確定の単勝人気、``market`` はオッズから見た勝率（レースの全頭で合計 1）、``categorical`` はカテゴリ特徴量の列名。
    5つの表と列は同じ行の並び。"""

    ids: pd.DataFrame
    features: pd.DataFrame
    label: pd.Series
    baseline: pd.Series
    popularity: pd.Series
    market: pd.Series
    categorical: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.ids)

    def where(self, rows: pd.Series | np.ndarray) -> LongshotData:
        mask = np.asarray(rows, dtype=bool)
        return LongshotData(self.ids[mask], self.features[mask], self.label[mask], self.baseline[mask], self.popularity[mask],
                            self.market[mask], self.categorical)

    def between(self, begin: pd.Timestamp | None, end: pd.Timestamp | None) -> LongshotData:
        """開催日が ``begin`` 以上 ``end`` 以下の行（None の端は区切らない）。"""
        days = self.ids[RACE_DATE]
        first = begin if begin is not None else pd.Timestamp.min
        last = end if end is not None else pd.Timestamp.max
        return self.where((days >= first) & (days <= last))

    @property
    def race_ids(self) -> pd.Series:
        return self.ids[RACE_ID]
