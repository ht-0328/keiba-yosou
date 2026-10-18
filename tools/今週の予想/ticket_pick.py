"""計画で複勝のほかに買う1点（単勝・馬単・馬連）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.review import names


@dataclass(frozen=True)
class TicketPick:
    """複勝のほかに買う1点。参加の種類（``kind``）は「勝負（単勝・馬単）」（当日の期待度「高」のレースの ◎ の単勝と馬単）か
    「勝負（組の期待値）」（当日の予想で組の期待値が線以上の馬連・馬単）。

    ``ticket_type`` は券種の名前、``combo`` は組番（馬番を2桁ずつ）、``label`` は人が読む並び（``3→1`` など）、
    ``value`` は期待値（単勝は ◎ の単勝の期待値、組の期待値の買い目は組の期待値。◎ の馬単は出さないので None）、
    ``odds`` は締め切り前のオッズ、``yen`` は金額。
    """

    ticket_type: str
    combo: str
    label: str
    value: float | None
    odds: float | None
    yen: int
    kind: str = names.MATCH_WIN
