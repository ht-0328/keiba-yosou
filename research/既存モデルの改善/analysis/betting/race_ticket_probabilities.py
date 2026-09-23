"""1レースの勝率から、7つの券種の買い目が当たる確率を出す。"""

from __future__ import annotations

import numpy as np

from 馬券の買い方の検証.analysis.ticket import TicketType

from ..race_probability import FinishOrderProbability

#: 複勝が2着までになる頭数の上限（7頭以下は2着まで）。
_SMALL_FIELD_UP_TO = 7


class RaceTicketProbabilities:
    """1レースの勝率 ``p``（馬番 − 1 の位置に並べた配列）から、券種ごとに「買い目が当たる確率」の表を作る。

    表は馬番 − 1 で引く（単勝・複勝は1次元、馬連・ワイド・馬単は2次元、3連複・3連単は3次元）。
    3連単の並びの確率（``FinishOrderProbability.ordered_triple``）を1回だけ作り、ほかの券種はそこから足して作る。
    複勝は、8頭以上なら3着以内、7頭以下なら2着以内に入る確率。
    """

    def __init__(self, order: FinishOrderProbability) -> None:
        self._order = order

    def of(self, p: np.ndarray, field_size: int) -> dict[TicketType, np.ndarray]:
        triple = self._order.ordered_triple(p)
        pair = self._order.ordered_pair(p)
        quinella = pair + pair.T
        trio = (triple + triple.transpose(0, 2, 1) + triple.transpose(1, 0, 2)
                + triple.transpose(1, 2, 0) + triple.transpose(2, 0, 1) + triple.transpose(2, 1, 0))
        top3 = trio.sum(axis=(1, 2)) / 2.0
        top2 = quinella.sum(axis=1)
        place = top2 if field_size <= _SMALL_FIELD_UP_TO else top3
        return {
            TicketType.WIN: p, TicketType.PLACE: place, TicketType.QUINELLA: quinella,
            TicketType.WIDE: trio.sum(axis=2), TicketType.EXACTA: pair, TicketType.TRIO: trio,
            TicketType.TRIFECTA: triple,
        }
