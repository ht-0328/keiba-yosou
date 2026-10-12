"""確定着順から、3連単・3連複の当たりの組を作る（関数だけ）。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import pairwise, permutations


def trifecta_winners(finishes: Mapping[int, int]) -> set[tuple[int, int, int]]:
    """馬番 → 確定着順 から、3連単の当たりの組。同着なら当たりの組は複数になる。

    3着以内の馬の並べ方のうち、着順が前から順に並んでいて（同着は入れ替えてよい）、各馬の着順がその欄の着順以下のものが当たり。
    例: 着順が 1・1・3 なら (a, b, c) と (b, a, c)。1・2・3・3 なら (a, b, c) と (a, b, d)。
    """
    placed = [horse for horse, finish in finishes.items() if 1 <= finish <= 3]
    return {order for order in permutations(placed, 3) if _consistent(order, finishes)}


def trio_winners(finishes: Mapping[int, int]) -> set[tuple[int, int, int]]:
    """3連複の当たりの組（馬番の小さい順）。"""
    return {tuple(sorted(order)) for order in trifecta_winners(finishes)}


def _consistent(order: tuple[int, int, int], finishes: Mapping[int, int]) -> bool:
    ranks = [finishes[horse] for horse in order]
    in_order = all(before <= after for before, after in pairwise(ranks))
    within_slot = all(rank <= slot for slot, rank in enumerate(ranks, start=1))
    return in_order and within_slot
