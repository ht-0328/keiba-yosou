"""3連単の買い目の候補（1着に◎か軸を置いて広めに流す）。"""

from __future__ import annotations

from itertools import permutations

from .combo_groups import FIRST_FIXED
from .race_horses import RaceHorses


class TrifectaCombos:
    """3連単の候補。1着は◎か1頭目の軸、2着・3着は消でない残りの馬全部。どれを買うかは期待値で決める
    （1点 100円で、期待値の高い順に広め＝上限 30点ほどまで）。"""

    def of(self, horses: RaceHorses, upset: bool) -> list[tuple[tuple[int, ...], str]]:
        firsts = {number for number in (horses.honmei, *horses.axes[:1]) if number is not None}
        return [((first, *rest), FIRST_FIXED) for first in sorted(firsts)
                for rest in permutations([number for number in horses.runners if number != first], 2)]
