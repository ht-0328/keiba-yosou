"""2着・3着の割り当てのならしの指数 λ を決める。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: λ の候補（0.50〜1.00 の 0.05 刻み。設計書 10 の 10.・14）。
LAMBDAS: np.ndarray = np.round(np.arange(0.50, 1.001, 0.05), 2)
#: ログを取るときに 0 にならないようにする下限。
_FLOOR = 1e-12


class OrderLambdaFitter:
    """λ の候補から、実際の 2着・3着の馬に付けた条件付きの確率の ``−log`` の合計が、レースの平均でいちばん小さいものを選ぶ。

    条件付きの確率は、1着（1・2着）を実際の馬に決めたときの、2着（3着）の確率（設計書 10 の 10.）。
    1〜3着のどれかに同着のあるレースと、3頭に満たないレースは数えない。
    """

    def fit(self, win: np.ndarray, race_ids: np.ndarray, finish: np.ndarray) -> float:
        """どれも同じ長さ（1行 = 1頭）。``win`` はレースの中で合計 1 の1着の確率、``finish`` は確定着順。"""
        table = pd.DataFrame({"race": race_ids, "p": np.asarray(win, dtype="float64"), "finish": finish})
        placed = self._placed(table)
        losses = [self._loss(table, placed, lam) for lam in LAMBDAS]
        return float(LAMBDAS[int(np.argmin(losses))])

    def _placed(self, table: pd.DataFrame) -> pd.DataFrame:
        """1〜3着が1頭ずつに決まるレースの、1〜3着の馬の確率（列 1・2・3、index はレース）。"""
        top = table[table["finish"].isin([1, 2, 3])]
        counts = top.groupby(["race", "finish"]).size().unstack(fill_value=0)
        clean = counts.index[(counts.reindex(columns=[1, 2, 3], fill_value=0) == 1).all(axis=1)]
        chosen = top[top["race"].isin(clean)]
        return chosen.pivot(index="race", columns="finish", values="p")[[1, 2, 3]]

    def _loss(self, table: pd.DataFrame, placed: pd.DataFrame, lam: float) -> float:
        total = (table["p"] ** lam).groupby(table["race"]).sum().reindex(placed.index)
        first, second, third = (placed[place] ** lam for place in (1, 2, 3))
        second_given_first = second / (total - first)
        third_given_two = third / (total - first - second)
        loss = -np.log(np.clip(second_given_first, _FLOOR, 1.0)) - np.log(np.clip(third_given_two, _FLOOR, 1.0))
        return float(loss.mean())
