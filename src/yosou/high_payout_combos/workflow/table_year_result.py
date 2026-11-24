"""組の表づくりの、1つの券種・1年ぶんの結果。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import TicketType


@dataclass(frozen=True)
class TableYearResult:
    """``TableWorkflow`` が1つの券種・1年について返す結果。

    - ``row_count``: 書いた行の数（対象の組の数）。``hit_count``: そのうち当たった組の数。
    - ``was_skipped``: 前に作った表があって、作り直さなかったか（そのときの行の数は 0）。
    """

    ticket_type: TicketType
    year: int
    row_count: int
    hit_count: int
    was_skipped: bool
