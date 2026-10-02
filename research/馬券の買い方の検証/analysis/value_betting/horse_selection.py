"""戦略の軸「馬の選び方」。"""

from __future__ import annotations

from enum import Enum

import pandas as pd

from yosou.longshots_in_top3.dataset.longshot_zone import LongshotZone

from . import columns as c

#: 穴馬モデルの区分の名前（予測の表の「区分」の値。穴馬の予想の ``LongshotZone`` と同じ）。
MID_ZONE, BIG_ZONE = LongshotZone.MID.value, LongshotZone.BIG.value


class HorseSelection(Enum):
    """穴馬モデルの区分で買う馬を絞る3通り（docs/05-round3-protocol.md の「戦略の軸」）。値は保存の名前。"""

    MID = "mid"
    BIG = "big"
    BOTH = "both"

    @property
    def label(self) -> str:
        """人が読む名前。"""
        return _LABELS[self]

    @property
    def zones(self) -> tuple[str, ...]:
        """買う対象にする穴馬の区分。"""
        return _ZONES[self]

    def rows_of(self, runners: pd.DataFrame) -> pd.Series:
        """1頭ごとの表の行ごとに、この選び方の対象か。"""
        return runners[c.LONGSHOT_ZONE].isin(self.zones)

    @classmethod
    def parse(cls, key: str) -> HorseSelection:
        """保存の名前から。知らなければ ``ValueError``。"""
        for selection in cls:
            if selection.value == key:
                return selection
        raise ValueError(f"知らない馬の選び方です: {key}（{' / '.join(selection.value for selection in cls)}）")


_LABELS: dict[HorseSelection, str] = {HorseSelection.MID: "中穴だけ", HorseSelection.BIG: "大穴だけ", HorseSelection.BOTH: "中穴と大穴"}
_ZONES: dict[HorseSelection, tuple[str, ...]] = {
    HorseSelection.MID: (MID_ZONE,), HorseSelection.BIG: (BIG_ZONE,), HorseSelection.BOTH: (MID_ZONE, BIG_ZONE),
}
