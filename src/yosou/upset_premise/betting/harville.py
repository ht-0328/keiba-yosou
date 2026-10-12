"""1着の確率から、3連単・3連複の組の確率を Harville の式で作る（関数だけ）。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import permutations


def trifecta_probability(win: Mapping[int, float], first: int, second: int, third: int) -> float:
    """1着 ``first``・2着 ``second``・3着 ``third`` の順に入る確率。

    Harville の式: P(i, j, k) = p_i × p_j / (1 − p_i) × p_k / (1 − p_i − p_j)。``win`` はレースで合計 1 の1着の確率。
    """
    p_first, p_second, p_third = win.get(first, 0.0), win.get(second, 0.0), win.get(third, 0.0)
    rest_after_first = 1.0 - p_first
    rest_after_second = rest_after_first - p_second
    if rest_after_first <= 0 or rest_after_second <= 0:
        return 0.0
    return p_first * p_second / rest_after_first * p_third / rest_after_second


def trio_probability(win: Mapping[int, float], horses: tuple[int, int, int]) -> float:
    """3頭がどの順でも1〜3着に入る確率（3連単の6通りの合計）。"""
    return sum(trifecta_probability(win, *order) for order in permutations(horses))
