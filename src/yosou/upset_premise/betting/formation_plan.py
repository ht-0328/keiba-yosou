"""第3段 乙 本線厚め: 3連単のフォーメーションで、組の確率の上位を厚くする。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import product

from .betting_rules import RACE_BUDGET_YEN
from .harville import trifecta_probability
from .race_horses import RaceHorses

#: 1着・2着・3着の欄に入れる頭数（docs/01 の 6）。
FIRST_COUNT, SECOND_COUNT, THIRD_COUNT = 3, 5, 8
#: 厚くする点数と、その1点の金額・残りの1点の金額。
THICK_COUNT, THICK_YEN, THIN_YEN = 10, 300, 100


class FormationPlan:
    """1着: 1着の確率の上位3頭 → 2着: 3着以内の確率の上位5頭 → 3着: 上位8頭（同じ馬は重ならない。最大 72点）。

    組の確率（Harville の式）の上位10点を 300円、残りを 100円で買う。当たっても払戻が 1万円を下回る組（トリガミ）は買わない。
    """

    name = "乙 本線厚め（3連単）"
    ordered = True

    def tickets(self, horses: RaceHorses, odds: Mapping[tuple[int, ...], float]) -> list[tuple[tuple[int, ...], int]]:
        """（組, 掛け金）の並び。"""
        win = horses.win_of()
        columns = (horses.by_win(FIRST_COUNT), horses.by_top3(SECOND_COUNT), horses.by_top3(THIRD_COUNT))
        combos = [combo for combo in product(*columns) if len(set(combo)) == 3 and combo in odds]
        ranked = sorted(combos, key=lambda combo: trifecta_probability(win, *combo), reverse=True)
        staked = [(combo, THICK_YEN if rank < THICK_COUNT else THIN_YEN) for rank, combo in enumerate(ranked)]
        return [(combo, stake) for combo, stake in staked if odds[combo] * stake >= RACE_BUDGET_YEN]
