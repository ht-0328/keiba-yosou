"""第3段 甲・丙: 当たれば必ず帯になる組だけを、帯に要る金額で買う。"""

from __future__ import annotations

import math
from collections.abc import Mapping
from itertools import combinations, permutations

from ..dataset import OBI_YEN
from .betting_rules import RACE_BUDGET_YEN, STAKE_MAX_YEN, STAKE_UNIT_YEN
from .harville import trifecta_probability, trio_probability
from .race_horses import RaceHorses

#: 組を作る馬の数（3着以内の確率の上位）。
POOL_COUNT = 8


class ObiStakePlan:
    """3着以内の確率の上位8頭で作った組のうち、帯に要る金額が 1,000円以下（オッズが 1,000倍以上）の組を、帯に要る金額で買う。

    帯に要る金額 = 100万円 ÷ オッズ（100円単位で切り上げ）。当たる確率 ÷ 金額 の高い順に、1レースの予算（1万円）に収まるまで積む。
    当たる確率 ÷ 金額 は、帯を当てる確率をいちばん高くする積み方で、帯に要る金額で買う組では「当たる確率 × オッズ」（期待値）の順とほぼ同じ。
    ``ordered`` が真なら3連単（甲）、偽なら3連複（丙）。
    ``line_yen`` は、当たったときに受け取りたい払戻の線（既定は帯の 100万円）。研究「百万馬券を当てる」で、
    10万円・30万円に下げた買い方を確かめるために変えられるようにした。
    """

    def __init__(self, ordered: bool, line_yen: int = OBI_YEN) -> None:
        self.ordered = ordered
        self._line_yen = line_yen
        kind = "甲" if ordered else "丙"
        ticket = "3連単" if ordered else "3連複"
        aim = "全部帯" if line_yen == OBI_YEN else f"当たれば{line_yen // 10_000}万円以上"
        self.name = f"{kind} {aim}（{ticket}）"

    def tickets(self, horses: RaceHorses, odds: Mapping[tuple[int, ...], float]) -> list[tuple[tuple[int, ...], int]]:
        """（組, 掛け金）の並び。"""
        win = horses.win_of()
        candidates = [(combo, self._stake(odds.get(combo), self._line_yen), self._probability(win, combo)) for combo in self._combos(horses)]
        affordable = [(combo, stake, probability) for combo, stake, probability in candidates if stake is not None]
        ranked = sorted(affordable, key=lambda item: item[2] / item[1], reverse=True)
        return self._within_budget([(combo, stake) for combo, stake, _ in ranked])

    @staticmethod
    def _within_budget(ranked: list[tuple[tuple[int, ...], int]]) -> list[tuple[tuple[int, ...], int]]:
        """並びの順に積み、足すと1万円を超える組は飛ばして、次の（金額の小さい）組を見る。"""
        chosen, spent = [], 0
        for combo, stake in ranked:
            fits = spent + stake <= RACE_BUDGET_YEN
            chosen += [(combo, stake)] if fits else []
            spent += stake if fits else 0
        return chosen

    def _combos(self, horses: RaceHorses) -> list[tuple[int, ...]]:
        pool = horses.by_top3(POOL_COUNT)
        if self.ordered:
            return list(permutations(pool, 3))
        return [tuple(sorted(combo)) for combo in combinations(pool, 3)]

    def _probability(self, win: Mapping[int, float], combo: tuple[int, ...]) -> float:
        if self.ordered:
            return trifecta_probability(win, *combo)
        return trio_probability(win, combo)

    @staticmethod
    def _stake(odds: float | None, line_yen: int) -> int | None:
        """線に要る金額（線 ÷ オッズを 100円単位で切り上げ）。オッズが無いか、1,000円を超えるなら None。"""
        if odds is None or not odds > 0:
            return None
        stake = math.ceil(line_yen / odds / STAKE_UNIT_YEN) * STAKE_UNIT_YEN
        return stake if stake <= STAKE_MAX_YEN else None
