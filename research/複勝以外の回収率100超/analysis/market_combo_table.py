"""1つの券種の1年ぶんのオッズから、レースごとに「市場が付けた組の確率」の表を作る。"""

from __future__ import annotations

from itertools import permutations

import numpy as np
import pandas as pd

from 回収率100超.analysis.tickets import MAX_HORSES, OddsBandCalibrator, TicketKind

#: 1レースの当たりの組の数。ワイドは3組（1-2着・1-3着・2-3着）当たるので、確率の合計を 3 にそろえる。
_WINNING_COMBOS: dict[str, float] = {"wide": 3.0}


class MarketComboTable:
    """オッズの逆数をレース内で合計 1（ワイドは 3）にそろえた値を、市場が付けた組の確率とする。

    表の番号は ``TicketKind.flat_index`` と同じ。順不同の券種（馬連・ワイド・3連複）は、元DB には
    馬番の小さい順の組しか無いので、並びを入れ替えた番号にも同じ値を入れる。例: 3連複の 1-2-3 の確率を、
    2-1-3・3-2-1 などの番号にも入れる（表の合計は並びの数だけ大きくなるが、引くときは昇順の番号で引く）。

    ``correction`` を渡すと、その券種自身のオッズの帯ごとの実績の倍率を掛けてから、合計をそろえ直す。
    人気薄の組が買われすぎている分を、市場の値段だけで直すためである（モデルは使わない）。
    """

    def __init__(self, kind: TicketKind, odds: pd.DataFrame, correction: OddsBandCalibrator | None = None) -> None:
        horses = [f"h{index + 1}" for index in range(kind.horses)]
        rows = odds.sort_values("rid", kind="stable")
        self._kind = kind
        self._correction = correction
        self._flat = kind.flat_index(rows[horses].to_numpy())
        self._inverse = 1.0 / rows["odds"].to_numpy(dtype=float)
        rid = rows["rid"].to_numpy()
        starts = np.flatnonzero(np.r_[True, rid[1:] != rid[:-1]])
        self._races = rid[starts]
        self._bounds = np.c_[starts, np.r_[starts[1:], len(rid)]]

    def get(self, rid: int) -> np.ndarray | None:
        """そのレースの組の確率の表（長さ 18 の「馬の数」乗）。オッズの無いレースは None。"""
        position = int(np.searchsorted(self._races, rid))
        if position >= len(self._races) or self._races[position] != rid:
            return None
        begin, end = self._bounds[position]
        dense = np.zeros(MAX_HORSES ** self._kind.horses)
        values = self._inverse[begin:end]
        if self._correction is not None:
            values = values * self._correction.factors(1.0 / values)
        dense[self._flat[begin:end]] = values / values.sum() * _WINNING_COMBOS.get(self._kind.key, 1.0)
        return dense if self._kind.ordered else self._fill_orders(dense)

    def _fill_orders(self, dense: np.ndarray) -> np.ndarray:
        """昇順の組の値を、並びを入れ替えた全部の番号に配る。"""
        shaped = dense.reshape((MAX_HORSES,) * self._kind.horses)
        filled = sum(shaped.transpose(order) for order in permutations(range(self._kind.horses)))
        return np.asarray(filled).ravel()
