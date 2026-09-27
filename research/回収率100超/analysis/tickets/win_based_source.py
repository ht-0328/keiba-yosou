"""1着の確率から、買い目の確率の表を作る出どころ。"""

from __future__ import annotations

import numpy as np

from .combo_probability import ComboProbability
from .race_win_table import RaceWinTable
from .ticket_kind import TicketKind


class WinBasedSource:
    """レースの1着の確率（モデルの予測）から、Stern の補正を入れた Harville の式で買い目の確率を作る。

    ``YearTicketScorer`` に渡す「確率の出どころ」の1つ。出どころは ``table(kind, rid)`` を持ち、
    そのレースの全部の買い目の確率を ``TicketKind.flat_index`` の番号の順に返す（予測の無いレースは None）。
    """

    def __init__(self, probability: ComboProbability, wins: RaceWinTable) -> None:
        self._probability = probability
        self._wins = wins

    def table(self, kind: TicketKind, rid: int) -> np.ndarray | None:
        wins = self._wins.get(rid)
        return None if wins is None else self._probability.table(kind, wins)
