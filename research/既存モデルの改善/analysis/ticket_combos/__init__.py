"""券種ごとの買い目の候補の作り方（利用者と決めた買い方）。

| 名前 | 仕事 |
|---|---|
| ``RaceHorses`` | 1レースの馬番の並び（消でない馬・人気・穴・軸・◎） |
| ``SingleCombos`` | 単勝・複勝の候補（消でない全部の馬） |
| ``PairCombos`` | 馬連・ワイド・馬単の候補（人気 + 穴。人気-人気は1点まで。荒れそうなら穴-穴も） |
| ``TrioCombos`` | 3連複の候補（1頭軸か2頭軸の流し） |
| ``TrifectaCombos`` | 3連単の候補（1着に◎か軸、2・3着は残り全部） |
| ``TicketSpec``・``TICKET_SPECS`` | 券種ごとの点数の上限と賭け金の決め方（3連単 100円・3連複 300円・ほかは予算を払戻均等） |
"""

from .combo_groups import FIRST_FIXED, HOLE_HOLE, ONE_AXIS, POPULAR_HOLE, POPULAR_POPULAR, SINGLE, TWO_AXES
from .pair_combos import PairCombos
from .race_horses import RaceHorses
from .single_combos import SingleCombos
from .ticket_spec import RACE_BUDGET, TICKET_SPECS, TicketSpec
from .trifecta_combos import TrifectaCombos
from .trio_combos import TrioCombos

__all__ = [
    "RaceHorses", "SingleCombos", "PairCombos", "TrioCombos", "TrifectaCombos", "TicketSpec", "TICKET_SPECS", "RACE_BUDGET",
    "SINGLE", "POPULAR_HOLE", "POPULAR_POPULAR", "HOLE_HOLE", "ONE_AXIS", "TWO_AXES", "FIRST_FIXED",
]
