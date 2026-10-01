"""締め切り前のオッズで1番人気だった馬の一覧。"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

#: 一覧の列（レースID と馬番）。
_KEY_COLUMNS = ["race_id", "horse_no"]
#: 馬番の分からない行に入れる、どの馬番とも一致しない値。
_NO_HORSE_NO = -1


@dataclass(frozen=True)
class PreDeadlineFavorites:
    """締め切り前の単勝オッズで1番人気だった馬（``race_id``・``horse_no`` の表。``PreDeadlineFavoriteRepository`` が読む）。

    確定の1番人気と比べるために、学習データに残す行を足すのと、評価で判定する行を選ぶのに使う（設計書 16 の 7）。
    空なら、締め切り前の1番人気は使わない（いつもの評価と学習）。
    """

    table: pd.DataFrame = field(default_factory=lambda: pd.DataFrame(columns=_KEY_COLUMNS))

    def contains(self, race_ids: pd.Series, horse_nos: pd.Series) -> pd.Series:
        """行ごとに、その馬が締め切り前の1番人気だったか（``race_ids`` と同じ index の真偽）。"""
        known = pd.MultiIndex.from_frame(self.table[_KEY_COLUMNS].astype({"race_id": str, "horse_no": int}))
        numbers = pd.to_numeric(horse_nos, errors="coerce").fillna(_NO_HORSE_NO).astype(int)
        pairs = pd.MultiIndex.from_arrays([race_ids.astype(str), numbers])
        return pd.Series(pairs.isin(known), index=race_ids.index)
