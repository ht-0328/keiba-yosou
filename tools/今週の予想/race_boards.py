"""1レースの締め切り前のオッズの板と複勝オッズを、1回だけ読む。"""

from __future__ import annotations

from typing import Any

import duckdb
import pandas as pd

from yosou.shared.repository import AnnouncedTicketOddsRepository, PlaceOddsRepository, TargetScope


class RaceBoards:
    """1レースの締め切り前のオッズの板（``AnnouncedTicketOddsRepository``。列 ``combo``・``odds`` に ``race_id`` を足したもの）を、
    券種ごとに初めて要るときに読み、同じ券種は読み直さない。

    1レースの買い目を組む間に、組の期待値・印の買い目の期待値・高配当の買い目・買い目のオッズが同じ板（とくに3連単）を何度も使うので、
    読むのを1回にする。板の無い券種は空の表。``ticket_type`` は券種（``TicketType`` か枠連の ``BRACKET``）。
    馬番ごとの複勝オッズ（最低・最高。``PlaceOddsRepository``）も、初めて要るときに1回だけ読む（``place_odds``）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, race_id: str) -> None:
        self._con = con
        self._race_id = race_id
        self._boards: dict[Any, pd.DataFrame] = {}
        self._place_odds: pd.DataFrame | None = None

    def of(self, ticket_type: Any) -> pd.DataFrame:
        if ticket_type not in self._boards:
            self._boards[ticket_type] = AnnouncedTicketOddsRepository(self._con, ticket_type).read(self._race_id).assign(race_id=self._race_id)
        return self._boards[ticket_type]

    def place_odds(self) -> pd.DataFrame:
        """1行 = 1頭。列は ``race_id``・``horse_no``・``place_odds_low``・``place_odds_high``（倍）。複勝オッズの無いレースは空の表。"""
        if self._place_odds is None:
            # 読む範囲はこの1レースだけ（リポジトリは、渡した関係の race_id だけを使う）
            scope = TargetScope(f"(SELECT '{int(self._race_id)}' AS race_id)")
            self._place_odds = PlaceOddsRepository(self._con).read(scope)
        return self._place_odds

    def many(self, ticket_types: tuple[Any, ...]) -> dict[Any, pd.DataFrame]:
        """券種 → 板（同じ券種が2回あっても1つ）。"""
        return {ticket_type: self.of(ticket_type) for ticket_type in dict.fromkeys(ticket_types)}
