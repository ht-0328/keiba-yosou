"""2回目: レースの型（セル）ごとに、8券種の中から券種と買い方を1つ選ぶ。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from 全レース全券種の買い方.analysis.cell_selector import CellChoice


@dataclass(frozen=True)
class TicketChoice:
    """1つの型で選んだ券種（``ticket``）と、その券種で選んだ型（``choice``。``CellChoice``）。"""

    ticket: str
    choice: CellChoice


class TicketChooser:
    """券種ごとにセルで選んだ型（``CellChoice``。当たりが足りる候補から下の端がいちばん高いもの）を並べ、セルごとに1つの券種を選ぶ（docs/03 の 3）。

    当たりが足りる（``enough``）券種の中で、回収率の 90% の幅の下の端がいちばん高いもの。足りる券種が無いセルは、全券種の中で下の端がいちばん高いもの。
    """

    def choose(self, choices: Mapping[str, Sequence[CellChoice]], cells: Sequence[str]) -> list[TicketChoice]:
        chosen = []
        for cell_index, _ in enumerate(cells):
            per_ticket = {ticket: per_cell[cell_index] for ticket, per_cell in choices.items()}
            enough = {ticket: choice for ticket, choice in per_ticket.items() if choice.enough}
            pool = enough or per_ticket
            ticket = max(pool, key=lambda name: _finite(pool[name].lower))
            chosen.append(TicketChoice(ticket, pool[ticket]))
        return chosen


def _finite(value: float) -> float:
    return value if np.isfinite(value) else -np.inf
