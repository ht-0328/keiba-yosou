"""第3段: 一律の買い方の比べる相手（2着・3着の重みも1着の確率にした、元の Harville の式）。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import permutations

from yosou.upset_premise.betting import BIG_ODDS, FlatPlan, RaceHorses, trifecta_probability


class PlainFlatPlan:
    """本番の一律（``FlatPlan``）と同じ買い方で、組の確率だけを元の Harville の式（2着・3着も1着の確率の比）にしたもの。

    本番の一律が採った「2着・3着は3着以内の確率の重み」（設計書 15 の 6）が、元の式よりどれだけ当てるかを比べるためにある。
    """

    ordered = True

    def __init__(self, stake_yen: int) -> None:
        self._flat = FlatPlan(stake_yen)
        self.stake_yen = stake_yen
        self.name = f"一律 {BIG_ODDS:,}倍以上（元の Harville・1点{stake_yen}円・{self._flat.count}点）"

    def tickets(self, horses: RaceHorses, odds: Mapping[tuple[int, ...], float]) -> list[tuple[tuple[int, ...], int]]:
        win = horses.win_of()
        combos = [combo for combo in permutations(horses.horse_numbers.tolist(), 3) if odds.get(combo, 0.0) >= BIG_ODDS]
        ranked = sorted(combos, key=lambda combo: (-trifecta_probability(win, *combo), combo))
        return [(combo, self.stake_yen) for combo in ranked[: self._flat.count]]
