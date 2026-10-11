"""計画で買う、単勝・馬単の1点。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TicketPick:
    """単勝・馬単の1点（参加の種類「勝負（単勝・馬単）」）。

    ``ticket_type`` は券種の名前、``combo`` は組番（馬番を2桁ずつ）、``label`` は人が読む並び（``3→1`` など）、
    ``value`` は期待値（単勝は ◎ の単勝の期待値。馬単は出さないので None）、``odds`` は締め切り前のオッズ、``yen`` は金額。
    """

    ticket_type: str
    combo: str
    label: str
    value: float | None
    odds: float | None
    yen: int
