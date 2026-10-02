"""1つの買い目。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import COMBO, RACE_ID, RULE, STAKE, STAKE_YEN, TICKET_TYPE

#: 買い目の表の列の並び。
TICKET_COLUMNS: tuple[str, ...] = (RACE_ID, TICKET_TYPE, COMBO, STAKE, RULE)


@dataclass(frozen=True)
class Ticket:
    """1つの買い目（レース・券種・馬番の並び・買い方の名前・金額）。

    ``horses`` は、馬単・3連単なら 1着から順の並び。馬連・ワイド・3連複は順番を問わないので、``combo`` で小さい順にそろえる。
    ``combo`` は払戻・確定オッズの表の組番と同じ形（馬番を2桁の0埋めでつなぐ。例 3連複 1-5-12 は ``010512``）。
    """

    race_id: str
    ticket_type: TicketType
    horses: tuple[int, ...]
    rule: str
    stake: int = STAKE_YEN

    def __post_init__(self) -> None:
        expected = self.ticket_type.spec.horse_count
        if len(self.horses) != expected or len(set(self.horses)) != expected:
            raise ValueError(f"{self.ticket_type.label}の買い目は、違う馬番が {expected}つです: {self.horses}")

    @property
    def combo(self) -> str:
        """組番（馬番を2桁の0埋めでつなぐ。順番を問わない券種は小さい順）。"""
        ordered = self.horses if self.ticket_type.spec.is_ordered else tuple(sorted(self.horses))
        return "".join(f"{horse:02d}" for horse in ordered)

    def as_row(self) -> dict[str, object]:
        """買い目の表の1行。"""
        return {RACE_ID: self.race_id, TICKET_TYPE: self.ticket_type.key, COMBO: self.combo, STAKE: self.stake, RULE: self.rule}

    @staticmethod
    def frame(tickets: Sequence[Ticket]) -> pd.DataFrame:
        """買い目の並びを、買い目の表（列 ``race_id``・``ticket_type``・``combo``・``stake``・``rule``）にする。空でも列はそろえる。"""
        return pd.DataFrame([ticket.as_row() for ticket in tickets], columns=list(TICKET_COLUMNS))
