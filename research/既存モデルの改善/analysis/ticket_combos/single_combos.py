"""単勝・複勝の買い目の候補（1頭）。"""

from __future__ import annotations

from .combo_groups import SINGLE
from .race_horses import RaceHorses


class SingleCombos:
    """消でない全部の馬を、単勝・複勝の候補にする。どの馬を買うかは期待値で決める（期待値の高い順に上限の点数まで）。"""

    def of(self, horses: RaceHorses, upset: bool) -> list[tuple[tuple[int, ...], str]]:
        return [((number,), SINGLE) for number in horses.runners]
