"""1開催日の確定の払戻（100円あたり）を、券種と組番で引けるように読む。"""

from __future__ import annotations

from datetime import date

import duckdb

from yosou.shared.betting import TicketType
from yosou.shared.betting.bracket_ticket import BRACKET
from yosou.shared.repository import PayoutRepository, RaceDayRange


class DayPayouts:
    """``read`` でその日の全レースの払戻を券種ごとに読み（``PayoutRepository``。速報の払戻も読む）、``yen`` で1点の払戻を引く。

    同着で同じ組に払戻が複数あれば足す。払戻の届いていないレース（まだ走っていない）は ``has`` が偽。枠連（組番は枠の番号を1桁ずつ）も読む。
    知らない券種の名前は ``yen`` が None。
    """

    def __init__(self) -> None:
        self._yen: dict[tuple[str, str, str], int] = {}
        self._races: set[str] = set()

    def read(self, con: duckdb.DuckDBPyConnection, day: date) -> DayPayouts:
        for label, ticket_type in self._kinds().items():
            rows = PayoutRepository(con, ticket_type).read(RaceDayRange(day, day))
            for row in rows.itertuples():
                key = (str(row.race_id), label, str(row.combo))
                self._yen[key] = self._yen.get(key, 0) + int(row.yen)
                self._races.add(str(row.race_id))
        return self

    def has(self, race_id: str) -> bool:
        """そのレースの払戻が届いているか。"""
        return race_id in self._races

    def yen(self, race_id: str, ticket_type: str, combo: str) -> int | None:
        """100円あたりの払戻（外れは 0）。知らない券種は None。"""
        if ticket_type not in self._kinds():
            return None
        return self._yen.get((race_id, ticket_type, combo), 0)

    @staticmethod
    def _kinds() -> dict:
        """券種の名前 → 払戻を読むときに渡す券種。"""
        return {**{kind.value: kind for kind in TicketType}, BRACKET.label: BRACKET}
