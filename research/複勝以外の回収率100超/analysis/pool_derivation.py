"""売上の大きい券種の組の確率から、ほかの券種の組の確率を作る。"""

from __future__ import annotations

from collections.abc import Callable
from itertools import permutations

import numpy as np

from 回収率100超.analysis.tickets import MAX_HORSES, TicketKind

_N = MAX_HORSES


class PoolDerivation:
    """3連単（または3連複）の市場の組の確率を足し合わせて、ほかの券種の組の確率にする。

    3連単の組の確率を t[i, j, k]（i が1着・j が2着・k が3着）とすると、
    - 単勝の i: t[i, ·, ·] の合計
    - 馬単の i→j: t[i, j, ·] の合計
    - 馬連の i-j: 馬単の i→j と j→i の和
    - 3連複の i-j-k: 6つの並びの和
    - ワイドの i-j: 3連複の i-j-k を k について足した値（i と j がどちらも3着以内）
    3連複の組の確率 r（並びを入れ替えた番号にも同じ値）からは、ワイドと3連複だけが作れる。
    どれも ``TicketKind.flat_index`` の番号の順に返す。
    """

    def __init__(self) -> None:
        self._from_trifecta: dict[str, Callable[[np.ndarray], np.ndarray]] = {
            "win": lambda t: t.sum(axis=(1, 2)),
            "exacta": lambda t: t.sum(axis=2),
            "quinella": lambda t: t.sum(axis=2) + t.sum(axis=2).T,
            "trio": self._all_orders,
            "wide": lambda t: self._all_orders(t).sum(axis=2),
            "trifecta": lambda t: t,
        }
        self._from_trio: dict[str, Callable[[np.ndarray], np.ndarray]] = {
            "trio": lambda r: r,
            "wide": lambda r: r.sum(axis=2),
        }

    def from_trifecta(self, kind: TicketKind, trifecta: np.ndarray) -> np.ndarray:
        return np.asarray(self._from_trifecta[kind.key](trifecta.reshape(_N, _N, _N))).ravel()

    def from_trio(self, kind: TicketKind, trio: np.ndarray) -> np.ndarray:
        return np.asarray(self._from_trio[kind.key](trio.reshape(_N, _N, _N))).ravel()

    def can_derive_from_trio(self, kind: TicketKind) -> bool:
        return kind.key in self._from_trio

    def _all_orders(self, table: np.ndarray) -> np.ndarray:
        return sum(table.transpose(order) for order in permutations(range(3)))
