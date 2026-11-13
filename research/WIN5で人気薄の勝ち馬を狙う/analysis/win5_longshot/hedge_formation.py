"""抑え（荒れる前提）のフォーメーション: 荒れそうなレースを本線に無い人気薄に差し替え、ほかのレースを予算の中で組む。"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.form_aptitude_win5_tickets.formation import Formation, FormationChoice, FormationValue
from yosou.form_aptitude_win5_tickets.leg import MARKET, SHARE
from yosou.form_aptitude_win5_tickets.payout import PayoutPool
from yosou.form_aptitude_win5_tickets.repository.win5_columns import HORSE_NO

from ..enrichment.race_market_shape import LONGSHOT_POPULARITY
from .hedge_candidate import BY_MARKET, HedgeCandidate
from .upset_legs import popularity_of


@dataclass(frozen=True)
class HedgeFormation:
    """``value`` は見積もり（今の組み方と同じ ``FormationValue``）。荒れそうなレースは人気薄の ``longshots`` 頭で決め打ちし、
    ほかのレースは確率の上位から選んで、点数が予算以下の頭数の並びのうち見積もりの払戻の合計がいちばん大きいものにする。
    今の組み方（``FormationSearch``）と同じく、全部の組の値を1回だけ出して累積の和で頭数の並びを比べる。
    組めなければ（荒れそうなレースに本線に無い人気薄がいない・点数が足りない）None。"""

    value: FormationValue

    def best(self, legs: Sequence[pd.DataFrame], main: Formation, upset: Sequence[int], candidate: HedgeCandidate,
             pool: PayoutPool) -> FormationChoice | None:
        fixed = {index: self._longshots(legs[index], main.legs[index], candidate) for index in upset}
        fixed = {index: picks for index, picks in fixed.items() if not picks.empty}
        if not fixed:
            return None
        remaining = candidate.budget // math.prod(len(picks) for picks in fixed.values())
        if remaining < 1:
            return None
        ordered = [fixed[index] if index in fixed else self._by_share(leg).head(remaining) for index, leg in enumerate(legs)]
        grid = self.value.grid(ordered, pool)
        free = [index for index in range(len(legs)) if index not in fixed]
        payout = self._cumulative(grid.expected_payout, fixed, free)
        probability = self._cumulative(grid.probability, fixed, free)
        points = self._points([len(ordered[index]) for index in free])
        allowed = np.where(points <= remaining, payout, -np.inf)
        position = np.unravel_index(int(np.argmax(allowed)), allowed.shape)
        sizes = dict(zip(free, (int(index) + 1 for index in position), strict=True))
        formation = Formation(tuple(tuple(int(n) for n in leg[HORSE_NO].head(sizes.get(index, len(leg))))
                                    for index, leg in enumerate(ordered)))
        return FormationChoice(formation, float(probability[position]), float(payout[position]))

    @staticmethod
    def _longshots(leg: pd.DataFrame, main_picks: tuple[int, ...], candidate: HedgeCandidate) -> pd.DataFrame:
        """人気薄のうち本線で選んでいない馬の上位 ``longshots`` 頭（``longshot_order`` の順）。"""
        key = MARKET if candidate.longshot_order == BY_MARKET else SHARE
        longshot = leg.loc[(popularity_of(leg) >= LONGSHOT_POPULARITY) & ~leg[HORSE_NO].astype(int).isin(main_picks)]
        return longshot.sort_values([key, HORSE_NO], ascending=[False, True]).head(candidate.longshots)

    @staticmethod
    def _by_share(leg: pd.DataFrame) -> pd.DataFrame:
        return leg.sort_values([SHARE, HORSE_NO], ascending=[False, True], kind="stable")

    @staticmethod
    def _cumulative(values: np.ndarray, fixed: dict[int, pd.DataFrame], free: list[int]) -> np.ndarray:
        """決め打ちのレースの向きは全部を足し、ほかのレースの向きは累積の和をとる（``[k-1, …]`` が上位 k 頭の合計）。"""
        summed = values.sum(axis=tuple(fixed))
        for axis in range(len(free)):
            summed = np.cumsum(summed, axis=axis)
        return summed

    @staticmethod
    def _points(sizes: Sequence[int]) -> np.ndarray:
        """頭数の並びごとの点数（ほかのレースの頭数のかけ算）。"""
        result = np.ones(sizes, dtype=np.int64)
        for axis, size in enumerate(sizes):
            shape = [1] * len(sizes)
            shape[axis] = size
            result = result * np.arange(1, size + 1, dtype=np.int64).reshape(shape)
        return result
