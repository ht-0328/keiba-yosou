"""勝つ確率の予想と世間の見立てから、3連単の買い目を選ぶ。

組の確率は、どちらも「強い順に1頭ずつ抜いていく」形で作る（``OrderProbabilities``）。
買うのは、予想の組の確率が線以上で、ずれ（予想 ÷ 世間の見立て）が線以上の組。オッズは見ない。
線は 2019〜2026年を年ごとに確かめて決めた（確率 1% 以上・ずれ 1.5倍以上で、8年の通算は 100% を超える。
学習の乱数の種を変えると 100% を割る年が出るので、毎年 100% 超とは言えない。確かめ中）。
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import permutations

from ばんえいの予想.order_probabilities import OrderProbabilities
from ばんえいの予想.trifecta_pick import TrifectaPick

#: 買う組の確率の下限。
DEFAULT_MIN_PROBABILITY = 0.01
#: 買う組のずれの下限。
DEFAULT_MIN_GAP = 1.5
#: 強いと書くずれの線。
DEFAULT_STRONG_GAP = 2.0
#: 買い目を出すレースの頭数の下限（確かめたのは 7頭以上のレース）。
MIN_RUNNERS = 7


class TrifectaPicker:
    def __init__(self, *, min_probability: float = DEFAULT_MIN_PROBABILITY, min_gap: float = DEFAULT_MIN_GAP,
                 strong_gap: float = DEFAULT_STRONG_GAP) -> None:
        self._min_probability = min_probability
        self._min_gap = min_gap
        self._strong_gap = strong_gap

    def pick(self, numbers: Sequence[int], model: Sequence[float], crowd: Sequence[float]) -> list[TrifectaPick]:
        """馬番・勝つ確率の予想・世間の見立て（同じ並び）から、買う組をずれの大きい順に。頭数が足りなければ空。"""
        if len(numbers) < MIN_RUNNERS:
            return []
        model_orders, crowd_orders = OrderProbabilities(model), OrderProbabilities(crowd)
        picks = []
        for first, second, third in permutations(range(len(numbers)), 3):
            probability = model_orders.order(first, second, third)
            if probability < self._min_probability:
                continue
            gap = probability / crowd_orders.order(first, second, third)
            if gap >= self._min_gap:
                order = (int(numbers[first]), int(numbers[second]), int(numbers[third]))
                picks.append(TrifectaPick(order=order, probability=probability, gap=gap, strong=gap >= self._strong_gap))
        return sorted(picks, key=lambda pick: (-pick.gap, pick.order))
