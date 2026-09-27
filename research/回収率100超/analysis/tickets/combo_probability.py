"""1レースの勝率から、券種ごとの全部の買い目の確率の表を作る。"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from ..market import SternProbabilities
from .ticket_kind import TicketKind


class ComboProbability:
    """勝率（馬番の順に 18個。出走しない馬番は 0）から、買い目の確率を1列に並べた表を作る。

    表の番号は ``TicketKind.flat_index`` と同じ。例えば 3連単なら、番号 652 が 3-1-5 の確率。
    2着・3着は Stern の補正を入れた Harville の式で割り当てる（研究のほかの部品と同じ）。
    """

    def __init__(self, stern: SternProbabilities) -> None:
        self._builders: dict[str, Callable[[np.ndarray], np.ndarray]] = {
            "win": lambda p: p,
            "wide": stern.wide,
            "quinella": stern.quinella,
            "exacta": stern.ordered_pair,
            "trio": stern.trio,
            "trifecta": stern.ordered_triple,
        }

    def table(self, kind: TicketKind, win_probability: np.ndarray) -> np.ndarray:
        """``kind`` の全部の買い目の確率（長さ 18 の「馬の数」乗）。"""
        return np.asarray(self._builders[kind.key](win_probability)).ravel()
