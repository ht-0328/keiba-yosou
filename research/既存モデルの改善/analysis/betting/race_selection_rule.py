"""勝負するレースの選び方の決まり1つ（検証期間で選ばせる候補の組）。"""

from __future__ import annotations

from dataclasses import dataclass

from .hardness_band import ALL_RACES, HardnessBand


@dataclass(frozen=True)
class RaceSelectionRule:
    """勝負するレースの選び方の決まり1つ。

    - ``key``・``name``: 保存と表に出す名前。
    - ``per_day``: 1開催日の上位のレース数の候補（None は全部）。検証期間で1つ選ぶ。
    - ``bands``: レースの堅さの帯の候補。検証期間で1つ選ぶ。
    - ``excluded_first``: 1番人気を消したレースを先に並べるか。
    - ``graded_in_cap``: 重賞も上位のレース数の枠に入れるか（False なら別枠）。

    例: 「1日3レースまで」は ``per_day`` = (1, 2, 3)。上限の中のいくつにするかは、検証期間で決める。
    """

    key: str
    name: str
    per_day: tuple[int | None, ...]
    bands: tuple[HardnessBand, ...] = (ALL_RACES,)
    excluded_first: bool = False
    graded_in_cap: bool = False
