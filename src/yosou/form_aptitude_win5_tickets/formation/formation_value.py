"""フォーメーションの全部の組の、当たる確率と見積もりの配当を出す。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO

from ..leg import MARKET, SHARE
from ..payout import PayoutCeiling, PayoutEstimator, PayoutFeatures, PayoutPool
from .combo_grid import ComboGrid
from .formation import Formation
from .formation_choice import FormationChoice


class FormationValue:
    """組の当たる確率（5頭のそろえた1着の確率のかけ算）と、見積もりの配当（市場の組の確率 → ``PayoutFeatures`` →
    ``PayoutEstimator`` → ``PayoutCeiling``）を、全部の組について表の計算でまとめて出す（設計書 16 の 3.、06 の図2）。

    組は「各レースの馬の並びの位置」の5次元の並び（``ComboGrid``）で持つ。1組ずつ Python の for 文で回さない。
    確率の出どころ（今のモデルか、区切りごとの予測か）は知らない。
    """

    def __init__(self, estimator: PayoutEstimator, ceiling: PayoutCeiling | None = None) -> None:
        self._estimator = estimator
        self._ceiling = ceiling or PayoutCeiling()
        self._features = PayoutFeatures()

    def grid(self, legs: Sequence[pd.DataFrame], pool: PayoutPool) -> ComboGrid:
        """``legs`` は5レースの、買い目に入れる馬だけを並べた確率の表（``SHARE``・``MARKET`` の列）。並びの順が ``ComboGrid`` の位置になる。"""
        probability = self._outer_product([leg[SHARE].to_numpy(dtype=float) for leg in legs])
        market = self._outer_product([leg[MARKET].to_numpy(dtype=float) for leg in legs])
        features = self._features.of(market.ravel(), pool.carry, pool.votes)
        payout = self._ceiling.apply(self._estimator.estimate(features), pool.money)
        return ComboGrid(probability, payout.reshape(market.shape))

    def of(self, formation: Formation, legs: Sequence[pd.DataFrame], pool: PayoutPool) -> FormationChoice:
        """1つのフォーメーションの、買い目のどれかが当たる確率と見積もりの払戻の合計。``legs`` は5レースの確率の表（全頭）。"""
        picked = [self._picked(leg, picks) for leg, picks in zip(legs, formation.legs, strict=True)]
        grid = self.grid(picked, pool)
        return FormationChoice(formation, float(grid.probability.sum()), float(grid.expected_payout.sum()))

    def _picked(self, leg: pd.DataFrame, picks: tuple[int, ...]) -> pd.DataFrame:
        """フォーメーションの馬番の順に、確率の表の行を取り出す。表に無い馬番は ``LookupError``。"""
        by_number = leg.set_index(leg[HORSE_NO].astype(int))
        missing = [number for number in picks if number not in by_number.index]
        if missing:
            raise LookupError(f"確率の表に無い馬番です: {missing}")
        return by_number.loc[list(picks)]

    def _outer_product(self, values: Sequence[np.ndarray]) -> np.ndarray:
        """5つの並びの、全部の組み合わせのかけ算（5次元の並び）。"""
        result = np.ones([len(each) for each in values])
        for axis, each in enumerate(values):
            shape = [1] * len(values)
            shape[axis] = len(each)
            result = result * each.reshape(shape)
        return result
