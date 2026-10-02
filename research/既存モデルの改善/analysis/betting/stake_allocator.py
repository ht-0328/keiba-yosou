"""1つの券種の買い目に、賭け金を割り振る（トリガミになる買い目は外す）。"""

from __future__ import annotations

import numpy as np

from ..ticket_combos import TicketSpec

#: 馬券の最小の単位（円）。
_UNIT = 100


class StakeAllocator:
    """1つの券種の買い目（オッズの並び）に賭け金を割り振る。

    - 3連単・3連複は、1点の金額が決まっている（``TicketSpec.stake_per_point``）。
    - ほかは、券種の予算を払戻均等で分ける。オッズの逆数に比例させ、100円単位に切り下げ、最低 100円。
      例: 予算 1,000円で 4倍と 12倍なら、750円と 250円 → 700円と 200円。
    - どれかの買い目が当たっても、払戻（賭け金 × オッズ）が券種の賭け金の合計以下（トリガミ）になるなら、その買い目の中で
      払戻がいちばん少ないものを外して、割り振り直す。全部の買い目が合計より多く戻るまで繰り返す。
    オッズは、複勝・ワイドでは最低オッズを使う（いちばん少ない払戻で確かめる）。
    """

    def allocate(self, spec: TicketSpec, odds: np.ndarray) -> np.ndarray:
        """買い目ごとの賭け金（外した買い目は 0）。"""
        kept = np.ones(len(odds), dtype=bool)
        while kept.any():
            stakes = np.where(kept, self._stakes(spec, odds, kept), 0.0)
            returns = np.where(kept, stakes * odds, np.inf)
            worst = int(returns.argmin())
            if returns[worst] > stakes.sum():
                return stakes
            kept[worst] = False
        return np.zeros(len(odds))

    def _stakes(self, spec: TicketSpec, odds: np.ndarray, kept: np.ndarray) -> np.ndarray:
        if spec.stake_per_point is not None:
            return np.full(len(odds), float(spec.stake_per_point))
        inverse = np.where(kept, 1.0 / odds, 0.0)
        share = spec.budget * inverse / inverse.sum()
        return np.maximum(np.floor(share / _UNIT) * _UNIT, _UNIT)
