"""印のルールの買い目（設計書「買うレースと買い目を決める」08 の 2）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import TicketType

#: 1単位の金額（円）。08 の 2 の「1点の額」は単位で書いてあるので、合計を金額で出すときに使う。
UNIT_YEN = 1000
#: 1点の額の最小の単位（円）。回収率は 1点 100円で数える。
POINT_YEN = 100
#: 複勝を買う期待値の線と、1レースで買う点数の上限（08 の「採用している券種（複勝）」）。
PLACE_VALUE_LINE = 1.25
PLACE_MAX_POINTS = 3
PLACE_STAKE_UNITS = 1.0


@dataclass(frozen=True)
class TicketRule:
    """1つの券種の印のルール。``positions`` は組の1頭目・2頭目・3頭目に置く印（券種の馬の数だけ）。

    ``△`` は3頭全部を指す。``in_design`` は設計書 08 の 2 の表にある券種か（馬単・3連単は、全券種をそろえるために
    ◎ を1着に固定した形で足したもので、設計書には無い）。
    """

    ticket_type: TicketType
    positions: tuple[tuple[str, ...], ...]
    stake_units: float
    in_design: bool

    @property
    def label(self) -> str:
        """表に出す券種の名前。設計書に無い券種は、そう分かるように書く。"""
        return self.ticket_type.label if self.in_design else f"{self.ticket_type.label}（設計書に無い）"


#: 印で組む券種のルール（08 の 2 の表の順に、馬単・3連単を足したもの）。複勝は印ではなく期待値で選ぶので、``MarkTickets`` が別に作る。
TICKET_RULES: tuple[TicketRule, ...] = (
    TicketRule(TicketType.WIN, (("◎",),), 1.0, True),
    TicketRule(TicketType.WIDE, (("◎",), ("☆", "注")), 1.0, True),
    TicketRule(TicketType.QUINELLA, (("◎",), ("○", "▲", "☆")), 0.5, True),
    TicketRule(TicketType.EXACTA, (("◎",), ("○", "▲", "☆")), 0.5, False),
    TicketRule(TicketType.TRIO, (("◎",), ("○", "▲", "☆"), ("○", "▲", "△", "☆")), 0.3, True),
    TicketRule(TicketType.TRIFECTA, (("◎",), ("○", "▲", "☆"), ("○", "▲", "△", "☆")), 0.1, False),
)
#: 表に並べる券種の順（複勝は単勝の次）。
TICKET_ORDER: tuple[TicketType, ...] = (
    TicketType.WIN, TicketType.PLACE, TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA, TicketType.TRIO, TicketType.TRIFECTA,
)


def rule_label(ticket_type: TicketType) -> str:
    """券種の表に出す名前（複勝は期待値のルール）。"""
    if ticket_type is TicketType.PLACE:
        return TicketType.PLACE.label
    return next(rule.label for rule in TICKET_RULES if rule.ticket_type is ticket_type)


def stake_units_of(ticket_type: TicketType) -> float:
    """券種の1点の額（単位）。"""
    if ticket_type is TicketType.PLACE:
        return PLACE_STAKE_UNITS
    return next(rule.stake_units for rule in TICKET_RULES if rule.ticket_type is ticket_type)


def combo_text(horses: tuple[int, ...]) -> str:
    """馬番の並びを、払戻・オッズの表の組番（2桁ずつ並べた文字列）にする。例: (1, 5) → ``0105``。"""
    return "".join(f"{int(horse):02d}" for horse in horses)
