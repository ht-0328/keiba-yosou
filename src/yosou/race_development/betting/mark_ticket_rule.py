"""印どおりの買い目を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import HORSE_NO, MARK, STAKE_YEN
from .mark import Mark
from .ticket import Ticket

#: 買い方の名前（モデルの印・人気順の印）。
MODEL_MARK_RULE = "印どおり（モデル）"
POPULARITY_MARK_RULE = "印どおり（人気順）"

_FIRST, _SECOND, _THIRD, _FOURTH = Mark.FIRST, Mark.SECOND, Mark.THIRD, Mark.FOURTH
#: 券種 → 印の並び（1点ずつ）。馬単・3連単は 1着から順の並び（設計書 16 の 8. の表）。
_PATTERNS: dict[TicketType, tuple[tuple[Mark, ...], ...]] = {
    TicketType.WIN: ((_FIRST,),),
    TicketType.PLACE: ((_FIRST,),),
    TicketType.WIDE: ((_FIRST, _SECOND), (_FIRST, _THIRD)),
    TicketType.QUINELLA: ((_FIRST, _SECOND), (_FIRST, _THIRD), (_FIRST, _FOURTH)),
    TicketType.EXACTA: ((_FIRST, _SECOND), (_FIRST, _THIRD), (_FIRST, _FOURTH)),
    TicketType.TRIO: ((_FIRST, _SECOND, _THIRD), (_FIRST, _SECOND, _FOURTH), (_FIRST, _THIRD, _FOURTH)),
    TicketType.TRIFECTA: (
        (_FIRST, _SECOND, _THIRD), (_FIRST, _SECOND, _FOURTH), (_FIRST, _THIRD, _SECOND), (_FIRST, _THIRD, _FOURTH),
    ),
}


class MarkTicketRule:
    """印から、券種ごとの印どおりの買い目を作る（設計書 16 の 8.）。1点 100円。

    | 券種 | 買い目 |
    |---|---|
    | 単勝・複勝 | ◎ |
    | ワイド | ◎-○、◎-▲ |
    | 馬連 | ◎-○、◎-▲、◎-△ |
    | 馬単 | ◎→○、◎→▲、◎→△ |
    | 3連複 | ◎-○-▲、◎-○-△、◎-▲-△ |
    | 3連単 | ◎→○→▲、◎→○→△、◎→▲→○、◎→▲→△ |

    印が足りない（4頭立て以下など）ときは、組める買い目だけを作る。☆と注は使わない。
    モデルの印にも人気順の印にも使い、``name``（買い目の表の ``rule``）で区別する。
    """

    def __init__(self, name: str = MODEL_MARK_RULE, stake: int = STAKE_YEN) -> None:
        self._name = name
        self._stake = stake

    def tickets(self, race_id: str, marks: pd.DataFrame, ticket_type: TicketType) -> pd.DataFrame:
        """``marks`` は印を付けた1レースの表（列 ``horse_no``・``mark``。``MarkAssigner.assign`` の戻り値）。

        戻り値は買い目の表（列 ``race_id``・``ticket_type``・``combo``・``stake``・``rule``）。
        """
        horse_of = {Mark(mark): int(horse) for horse, mark in zip(marks[HORSE_NO], marks[MARK]) if mark}
        patterns = [pattern for pattern in _PATTERNS[ticket_type] if all(mark in horse_of for mark in pattern)]
        return Ticket.frame([
            Ticket(race_id, ticket_type, tuple(horse_of[mark] for mark in pattern), self._name, self._stake) for pattern in patterns
        ])
