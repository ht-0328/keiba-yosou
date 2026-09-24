"""3連複の買い目の候補（軸から流す）。"""

from __future__ import annotations

from itertools import combinations

from .combo_groups import ONE_AXIS, TWO_AXES
from .race_horses import RaceHorses


class TrioCombos:
    """3連複の候補。軸が2頭なら「軸1-軸2-相手」（2頭軸）、1頭なら「軸-相手-相手」（1頭軸）。
    相手は消でない残りの馬全部で、どれを買うかは期待値で決める（期待値の高い順に上限の点数まで）。"""

    def of(self, horses: RaceHorses, upset: bool) -> list[tuple[tuple[int, ...], str]]:
        if not horses.axes:
            return []
        others = [number for number in horses.runners if number not in horses.axes]
        if len(horses.axes) >= 2:
            first, second = horses.axes[:2]
            return [(tuple(sorted((first, second, other))), TWO_AXES) for other in others]
        return [(tuple(sorted((horses.axes[0], *pair))), ONE_AXIS) for pair in combinations(others, 2)]
