"""1着の確率から、3連単・3連複の組の確率を Harville の式で作る（関数だけ）。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import permutations


def trifecta_probability(win: Mapping[int, float], first: int, second: int, third: int,
                         place: Mapping[int, float] | None = None) -> float:
    """1着 ``first``・2着 ``second``・3着 ``third`` の順に入る確率。

    Harville の式: P(i, j, k) = p_i × p_j / (1 − p_i) × p_k / (1 − p_i − p_j)。``win`` はレースで合計 1 の1着の確率。
    ``place`` を渡すと、2着・3着は ``place`` の重み（3着以内の確率など。合計は 1 でなくてよい）の比で決める（設計書 15 の 6）:
    P(i, j, k) = p_i × q_j / (Q − q_i) × q_k / (Q − q_i − q_j)。Q は ``place`` の合計。省略すると ``win`` を重みにする（元の式）。
    """
    weights = win if place is None else place
    total = 1.0 if place is None else sum(weights.values())
    p_first = win.get(first, 0.0)
    q_first, q_second, q_third = weights.get(first, 0.0), weights.get(second, 0.0), weights.get(third, 0.0)
    rest_after_first = total - q_first
    rest_after_second = rest_after_first - q_second
    if rest_after_first <= 0 or rest_after_second <= 0:
        return 0.0
    return p_first * q_second / rest_after_first * q_third / rest_after_second


def trio_probability(win: Mapping[int, float], horses: tuple[int, int, int],
                     place: Mapping[int, float] | None = None) -> float:
    """3頭がどの順でも1〜3着に入る確率（3連単の6通りの合計）。``place`` は ``trifecta_probability`` と同じ。"""
    return sum(trifecta_probability(win, *order, place=place) for order in permutations(horses))
