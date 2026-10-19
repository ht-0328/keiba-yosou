"""枠連（``TicketType`` には入れない券種）。"""

from __future__ import annotations

from dataclasses import dataclass

from .ticket_type_spec import TicketTypeSpec

#: 枠連の元DB での表し方。組番は枠の番号を1桁ずつ並べた2文字（例 ``"18"`` = 1枠と8枠）。払戻率は馬連と同じ 77.5%。
_SPEC = TicketTypeSpec("bracket", 2, False, "hr__枠連払戻", "組番", "o1", "o1__枠連オッズ", False, 0.775)


@dataclass(frozen=True)
class BracketTicket:
    """枠連。展開の予想など、``TicketType`` の全部の券種を回す処理に入れないため、``TicketType`` とは別に置く。

    オッズ・払戻を読む部品（``FinalOddsRepository``・``AnnouncedTicketOddsRepository``・``TicketOddsRepository``・``PayoutRepository``）は
    ``spec`` だけを使うので、``TicketType`` の代わりにそのまま渡せる。券種の名前から引くときは ``ticket_kind``。
    組番の1文字が1つの枠（馬番の2桁ではない）なので、組番を馬番に分ける処理には渡さない。
    """

    label: str = "枠連"

    @property
    def key(self) -> str:
        return _SPEC.key

    @property
    def spec(self) -> TicketTypeSpec:
        return _SPEC

    @property
    def is_combination(self) -> bool:
        return True


#: 枠連（ほかの券種の ``TicketType.WIN`` などと同じように使う、ただ1つの値）。
BRACKET = BracketTicket()
