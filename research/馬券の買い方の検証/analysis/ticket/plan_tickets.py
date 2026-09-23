"""1レース × 1買い方の買い目。"""

from __future__ import annotations

from dataclasses import dataclass

from .ticket import Ticket


@dataclass(frozen=True)
class PlanTickets:
    """1レースに1つの買い方を当てた結果。買い目の並びか、見送った理由のどちらか。"""

    tickets: tuple[Ticket, ...]
    skipped: str | None = None

    @property
    def points(self) -> int:
        return len(self.tickets)

    @classmethod
    def skip(cls, reason: str) -> PlanTickets:
        return cls((), reason)
