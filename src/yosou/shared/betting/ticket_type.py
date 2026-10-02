"""券種を表す値。"""

from __future__ import annotations

from enum import Enum

from .ticket_type_spec import TicketTypeSpec


class TicketType(Enum):
    """扱う7つの券種。値は人が読む名前で、表の見出しや ``--bet`` の書き方にそのまま使う。

    券種ごとの表の名前や組の形は ``spec``（``TicketTypeSpec``）から取る。WIN5 と枠連は扱わない。
    """

    WIN = "単勝"
    PLACE = "複勝"
    QUINELLA = "馬連"
    EXACTA = "馬単"
    WIDE = "ワイド"
    TRIO = "3連複"
    TRIFECTA = "3連単"

    @property
    def label(self) -> str:
        """人が読む名前。"""
        return self.value

    @property
    def key(self) -> str:
        """英語の短い名前（列名やファイル名の頭）。"""
        return self.spec.key

    @property
    def spec(self) -> TicketTypeSpec:
        """元DB での表し方と買い目の形。"""
        return _SPECS[self]

    @property
    def is_combination(self) -> bool:
        """2頭以上の組み合わせを当てる券種か（払戻の列が組番になる）。"""
        return self.spec.horse_count > 1

    @classmethod
    def parse(cls, text: str) -> TicketType:
        """``3連複`` のような書き方から券種を返す。知らなければ ``ValueError``。"""
        for ticket_type in cls:
            if ticket_type.label == text.strip():
                return ticket_type
        raise ValueError(f"知らない券種です: {text}（{TICKET_TYPE_CHOICES}）")

    @classmethod
    def of_key(cls, key: str) -> TicketType:
        """``trio`` のような英語の短い名前から券種を返す。知らなければ ``ValueError``。"""
        for ticket_type in cls:
            if ticket_type.key == key:
                return ticket_type
        raise ValueError(f"知らない券種の名前です: {key}")


_SPECS: dict[TicketType, TicketTypeSpec] = {
    TicketType.WIN: TicketTypeSpec("win", 1, False, "hr__単勝払戻", "馬番", "o1", "o1__単勝オッズ", False),
    TicketType.PLACE: TicketTypeSpec("place", 1, False, "hr__複勝払戻", "馬番", "o1", "o1__複勝オッズ", True),
    TicketType.QUINELLA: TicketTypeSpec("quinella", 2, False, "hr__馬連払戻", "組番", "o2", "o2__馬連オッズ", False),
    TicketType.EXACTA: TicketTypeSpec("exacta", 2, True, "hr__馬単払戻", "組番", "o4", "o4__馬単オッズ", False),
    TicketType.WIDE: TicketTypeSpec("wide", 2, False, "hr__ワイド払戻", "組番", "o3", "o3__ワイドオッズ", True),
    TicketType.TRIO: TicketTypeSpec("trio", 3, False, "hr__3連複払戻", "組番", "o5", "o5__3連複オッズ", False),
    TicketType.TRIFECTA: TicketTypeSpec("trifecta", 3, True, "hr__3連単払戻", "組番", "o6", "o6__3連単オッズ", False),
}
#: 券種の書き方の案内（コマンドの説明と、誤りの文面に使う）。
TICKET_TYPE_CHOICES = " / ".join(ticket_type.label for ticket_type in TicketType)
