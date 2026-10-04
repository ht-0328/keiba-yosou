"""買い目や ◎ の成績を数えるときの、レースの絞り込み。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.win_value import HIGH

from 今週の予想.forecast_columns import EXPECTATION

from 印の成績.filter_columns import AGREEMENT, POOL_BACKED

#: 絞り込みの名前に使う言葉。
AGREE_LABEL, DISAGREE_LABEL = "2モデル一致", "2モデル不一致"
POOL_LABEL, NO_POOL_LABEL = "3連単の支持あり", "3連単の支持なし"


@dataclass(frozen=True)
class RaceFilter:
    """レースの絞り込み1つ。``high_only`` なら期待度「高」のレースだけ、``flags`` の旗が全部真で、``off_flags`` の旗が全部偽のレース。

    旗はレースの全頭に同じ値が入る列（``agreement``・``pool_backed``）。表に無い旗は偽とみなす。
    """

    label: str
    high_only: bool = False
    flags: tuple[str, ...] = ()
    off_flags: tuple[str, ...] = ()

    def select(self, frame: pd.DataFrame) -> pd.Series:
        """行ごとの真偽（index は ``frame`` と同じ）。"""
        chosen = pd.Series(True, index=frame.index)
        if self.high_only:
            chosen &= frame[EXPECTATION] == HIGH
        for flag in self.flags:
            chosen &= self._flag(frame, flag)
        for flag in self.off_flags:
            chosen &= ~self._flag(frame, flag)
        return chosen

    def _flag(self, frame: pd.DataFrame, flag: str) -> pd.Series:
        if flag not in frame.columns:
            return pd.Series(False, index=frame.index)
        return frame[flag].fillna(False).astype(bool)


ALL_RACES = RaceFilter("全レース")
HIGH_RACES = RaceFilter(f"期待度 {HIGH}", high_only=True)
HIGH_AGREE = RaceFilter(f"期待度 {HIGH}・{AGREE_LABEL}", high_only=True, flags=(AGREEMENT,))
HIGH_DISAGREE = RaceFilter(f"期待度 {HIGH}・{DISAGREE_LABEL}", high_only=True, off_flags=(AGREEMENT,))
HIGH_POOL = RaceFilter(f"期待度 {HIGH}・{POOL_LABEL}", high_only=True, flags=(POOL_BACKED,))
HIGH_NO_POOL = RaceFilter(f"期待度 {HIGH}・{NO_POOL_LABEL}", high_only=True, off_flags=(POOL_BACKED,))
HIGH_AGREE_POOL = RaceFilter(f"期待度 {HIGH}・{AGREE_LABEL}・{POOL_LABEL}", high_only=True, flags=(AGREEMENT, POOL_BACKED))
#: 買い方ごとの表（表7・表8）に並べる絞り込み。
TARGETS: tuple[RaceFilter, ...] = (ALL_RACES, HIGH_RACES, HIGH_AGREE, HIGH_POOL, HIGH_AGREE_POOL)
#: ◎ の期待度ごとの表（表6）に足す絞り込み（「高」の内訳）。
TOP_FILTERS: tuple[RaceFilter, ...] = (HIGH_AGREE, HIGH_DISAGREE, HIGH_POOL, HIGH_NO_POOL, HIGH_AGREE_POOL)
