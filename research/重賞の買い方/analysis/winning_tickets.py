"""案2（勝てる券種）: セルごとに、選ぶ期間の回収率が 100% 以上だった券種を決める。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from 全レース全券種の買い方.analysis.cell_selector import CellChoice


class WinningTickets:
    """券種ごとにセルで選んだ型（``CellChoice``）から、セルごとに買う券種を決める（docs/01 の 5 の案2）。

    選ぶ期間の回収率が 100% 以上の券種を全部。1つも無いセルは、回収率の 90% の幅の下の端がいちばん高い券種を1つ。
    戻り値はセル → 買う券種の並び（``tickets`` の順）。
    """

    def choose(self, choices: Mapping[str, Sequence[CellChoice]], tickets: Sequence[str], cells: Sequence[str]) -> dict[str, list[str]]:
        chosen: dict[str, list[str]] = {}
        for cell_index, cell in enumerate(cells):
            per_ticket = {ticket: choices[ticket][cell_index] for ticket in tickets if ticket in choices}
            winners = [ticket for ticket, choice in per_ticket.items() if choice.recovery >= 1.0]
            if not winners and per_ticket:
                winners = [max(per_ticket, key=lambda ticket: _finite(per_ticket[ticket].lower))]
            chosen[cell] = winners
        return chosen


def _finite(value: float) -> float:
    return value if np.isfinite(value) else -np.inf
