"""同じレースの馬の値の、何番目に大きい（小さい）値。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .race_order import RaceOrder


class RaceOrderStatistic:
    """レースごとに、値を並べたときの n 番目の値を出す（例: 先頭率の2位、上がりの速さの2番目に小さい値）。

    数える向き（大きい値から・小さい値から）は、作るときに ``RaceOrder`` で決める。
    レースごとに関数を呼ぶと、3万レースを超える学習データでは遅いので、1回の並べ替えでまとめて出す。
    欠損値は数えない。n 番目が無いレース（値のある馬が n 頭に満たない）は欠損値。
    """

    def __init__(self, order: RaceOrder) -> None:
        self._order = order

    def nth(self, values: pd.Series, race: pd.Series, n: int) -> pd.Series:
        """レースごとの n 番目（1 から数える）の値。index はレースID。"""
        position, ordered = self._positions(values, race)
        return ordered.loc[position.to_numpy() == n - 1].set_index("race")["value"]

    def nth_for_rows(self, values: pd.Series, race: pd.Series, n: int) -> pd.Series:
        """``nth`` の値を、行ごと（``values`` と同じ index）に配ったもの。"""
        by_race = self.nth(values, race, n)
        return pd.Series(by_race.reindex(race.to_numpy()).to_numpy(), index=values.index)

    def mean_of_top(self, values: pd.Series, race: pd.Series, k: int) -> pd.Series:
        """レースごとの、上位 k 頭（数える向きの先頭から k 頭）の値の平均。index はレースID。"""
        position, ordered = self._positions(values, race)
        return ordered.loc[position.to_numpy() < k].groupby("race", sort=False)["value"].mean()

    def best_other(self, values: pd.Series, race: pd.Series) -> pd.Series:
        """自分を除いた、同じレースの馬のいちばん良い値（数える向きの先頭の値）。自分がいちばんなら2番目。"""
        best = self.nth_for_rows(values, race, 1)
        second = self.nth_for_rows(values, race, 2)
        is_best = values <= best if self._order.ascending else values >= best
        return pd.Series(np.where(is_best, second, best), index=values.index)

    def _positions(self, values: pd.Series, race: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
        """レースごとに値を数える向きに並べた表（欠損値は除く）と、レースの中での位置（0 から）。"""
        table = pd.DataFrame({"race": race.to_numpy(), "value": values.to_numpy()}).dropna()
        ordered = table.sort_values(["race", "value"], ascending=[True, self._order.ascending], kind="stable")
        return ordered.groupby("race", sort=False).cumcount(), ordered
