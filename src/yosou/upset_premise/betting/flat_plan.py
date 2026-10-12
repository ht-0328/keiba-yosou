"""第3段 一律: 1,000倍以上の3連単の組を、組の確率の高い順に、一律の金額で買う。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import permutations

from .betting_rules import BIG_ODDS, DEFAULT_FLAT_STAKE_YEN, RACE_BUDGET_YEN, STAKE_UNIT_YEN
from .harville import trifecta_probability
from .race_horses import RaceHorses


class FlatPlan:
    """全頭で作った3連単の組のうち、オッズが 1,000倍以上の組を、組の確率の高い順に、1点 ``stake_yen`` で予算（1万円）に収まる点数だけ買う。

    組の確率は、1着は荒れる前提の1着の確率、2着・3着は ``RaceHorses.place_of()`` の重み（今の予想と荒れる前提の予想の
    3着以内の確率の平均）で、Harville の式から作る（設計書 15 の 6）。同じ確率なら馬番の小さい組を先にする。
    1点の金額は一律で、100円なら 100点、300円なら 33点、500円なら 20点になる（設計書 15 の 4）。
    """

    ordered = True

    def __init__(self, stake_yen: int = DEFAULT_FLAT_STAKE_YEN) -> None:
        if stake_yen <= 0 or stake_yen % STAKE_UNIT_YEN or stake_yen > RACE_BUDGET_YEN:
            raise ValueError(f"1点の金額は {STAKE_UNIT_YEN}円単位で {RACE_BUDGET_YEN:,}円以下にしてください: {stake_yen}")
        self.stake_yen = stake_yen
        self.count = RACE_BUDGET_YEN // stake_yen
        self.name = f"一律 {BIG_ODDS:,}倍以上（3連単・1点{stake_yen}円・{self.count}点）"

    def tickets(self, horses: RaceHorses, odds: Mapping[tuple[int, ...], float]) -> list[tuple[tuple[int, ...], int]]:
        """（組, 掛け金）の並び。オッズが無い組・1,000倍未満の組は買わない。"""
        win, place = horses.win_of(), horses.place_of()
        combos = [combo for combo in permutations(horses.horse_numbers.tolist(), 3) if odds.get(combo, 0.0) >= BIG_ODDS]
        ranked = sorted(combos, key=lambda combo: (-trifecta_probability(win, *combo, place=place), combo))
        return [(combo, self.stake_yen) for combo in ranked[: self.count]]
