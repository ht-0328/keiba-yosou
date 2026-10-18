"""組の期待値の買い方で、買うレースを中身で絞る条件1つ（研究「レースの種類ごとの買い方」の docs/03）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 条件に使えるレースの中身の列。頭数・1番人気の単勝オッズ・◎ の単勝の期待値（作るのは ``ComboRaceTraits``）。
FIELD_SIZE, FAVORITE_ODDS, TOP_VALUE = "field_size", "favorite_odds", "top_value"
TRAIT_COLUMNS: tuple[str, ...] = (FIELD_SIZE, FAVORITE_ODDS, TOP_VALUE)


@dataclass(frozen=True)
class RaceCondition:
    """レースの中身の列 ``trait``（``ComboRaceTraits`` の列）が ``low`` 以上 ``high`` 以下のレースだけ買う条件（None の端は区切らない）。
    中身が分からないレース（欠損値）は買わない。``text`` は人が読む条件。

    例: ``RaceCondition("favorite_odds", 2.9, None, "1番人気が 2.9倍以上")`` は、1番人気の単勝オッズが 2.9倍以上のレースだけ。
    """

    trait: str
    low: float | None
    high: float | None
    text: str

    def passes(self, races: pd.DataFrame) -> pd.Series:
        """行ごとに、条件に合うか（真偽）。"""
        values = races[self.trait]
        mask = values.notna()
        if self.low is not None:
            mask &= values >= self.low
        if self.high is not None:
            mask &= values <= self.high
        return mask
