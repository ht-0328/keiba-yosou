"""1レースの推奨買目のまとまり（券種ごとの点と、出さないときの理由）。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .recommendation import Recommendation

#: 券種の並び（文と画像に出す順）。
TICKET_ORDER: tuple[str, ...] = ("単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "3連複", "3連単")


@dataclass(frozen=True)
class RecommendationSet:
    rows: tuple[Recommendation, ...]
    #: 1点も無いときの理由（例 ``10頭以下は推奨買目の対象外``）。あっても空でよい。
    reason: str = ""

    @property
    def none(self) -> bool:
        return not self.rows

    @property
    def points(self) -> int:
        return len(self.rows)

    @property
    def yen(self) -> int:
        return sum(row.yen for row in self.rows)

    def by_ticket(self) -> dict[str, list[Recommendation]]:
        """券種 → その券種の点（``TICKET_ORDER`` の順。券種の中は番号の順。無い券種は入れない）。"""
        grouped: dict[str, list[Recommendation]] = {}
        for ticket in TICKET_ORDER:
            chosen = sorted((row for row in self.rows if row.ticket == ticket), key=lambda row: row.numbers)
            if chosen:
                grouped[ticket] = chosen
        return grouped

    def lines(self) -> list[str]:
        """券種ごとに1行（例 ``枠連 3-5・4-8``）。"""
        return [f"{ticket} {'・'.join(row.label for row in rows)}" for ticket, rows in self.by_ticket().items()]

    def merged(self, extra: Iterable[Recommendation]) -> RecommendationSet:
        """``extra`` の点を足す（同じ券種・同じ組は1度だけ）。理由は残す。"""
        rows = list(self.rows)
        keys = {row.key for row in rows}
        for row in extra:
            if row.key in keys:
                continue
            rows.append(row)
            keys.add(row.key)
        return RecommendationSet(tuple(rows), self.reason)
