"""印から買う買い目のルールの一覧（利用者と決めたもの）。"""

from __future__ import annotations

from 馬券の買い方の検証.analysis.ticket import TicketType

from .mark import Mark
from .mark_rule import MarkRule

_HONMEI, _TAIKOU, _TANANA, _RENSHITA, _ANA, _CHUI = (
    Mark.HONMEI, Mark.TAIKOU, Mark.TANANA, Mark.RENSHITA, Mark.ANA, Mark.CHUI,
)
#: 2頭の並び: そのまま。表裏（1着と2着の入れ替え）。
_PAIR, _PAIR_BOTH = ((0, 1),), ((0, 1), (1, 0))
#: 3頭の並び: そのまま。3連単は、そのまま・1着と2着の入れ替え・2着と3着の入れ替え・両方の入れ替え（▲→X→○ の形）の4通り。
_TRIPLE = ((0, 1, 2),)
_TRIPLE_SWAPS = ((0, 1, 2), (1, 0, 2), (0, 2, 1), (1, 2, 0))

#: いつも買う（◎から）。カット前の点数は、単勝・複勝 1、馬連 5、ワイド 7、馬単 10、3連複 11、3連単 46。
ALWAYS_RULES: tuple[MarkRule, ...] = (
    MarkRule(TicketType.WIN, ((_HONMEI,),), ((0,),)),
    MarkRule(TicketType.PLACE, ((_HONMEI,),), ((0,),)),
    MarkRule(TicketType.QUINELLA, ((_HONMEI,), (_TAIKOU, _TANANA, _RENSHITA)), _PAIR),
    MarkRule(TicketType.WIDE, ((_HONMEI,), (_TAIKOU, _TANANA, _RENSHITA, _ANA, _CHUI)), _PAIR),
    MarkRule(TicketType.EXACTA, ((_HONMEI,), (_TAIKOU, _TANANA, _RENSHITA)), _PAIR_BOTH),
    MarkRule(TicketType.TRIO, ((_HONMEI,), (_TAIKOU, _TANANA), (_TAIKOU, _TANANA, _RENSHITA, _ANA, _CHUI)), _TRIPLE),
    MarkRule(TicketType.TRIFECTA, ((_HONMEI,), (_TAIKOU, _TANANA), (_TAIKOU, _TANANA, _RENSHITA, _ANA, _CHUI)),
             _TRIPLE_SWAPS),
)

#: ◎が危ういときだけ足す押さえ（◎を外した相手同士）。カット前の点数は、馬連・ワイド 1、馬単 2、3連複 5、3連単 20。
COVER_RULES: tuple[MarkRule, ...] = (
    MarkRule(TicketType.QUINELLA, ((_TAIKOU,), (_TANANA,)), _PAIR, cover=True),
    MarkRule(TicketType.WIDE, ((_TAIKOU,), (_TANANA,)), _PAIR, cover=True),
    MarkRule(TicketType.EXACTA, ((_TAIKOU,), (_TANANA,)), _PAIR_BOTH, cover=True),
    MarkRule(TicketType.TRIO, ((_TAIKOU,), (_TANANA,), (_RENSHITA, _ANA, _CHUI)), _TRIPLE, cover=True),
    MarkRule(TicketType.TRIFECTA, ((_TAIKOU,), (_TANANA,), (_RENSHITA, _ANA, _CHUI)), _TRIPLE_SWAPS, cover=True),
)

#: 全部のルール。
MARK_RULES: tuple[MarkRule, ...] = ALWAYS_RULES + COVER_RULES
