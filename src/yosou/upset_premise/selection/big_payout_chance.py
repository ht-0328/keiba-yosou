"""第1段: 予想が見た 1,000倍以上になる確率。"""

from __future__ import annotations

from collections.abc import Mapping
from itertools import permutations

from ..betting import BIG_ODDS, RaceHorses, trifecta_probability


class BigPayoutChance:
    """今の予想（全部のレースで学んだ手本の予想）の1着の確率から、Harville の式で全部の3連単の組の確率を出し、
    オッズが 1,000倍以上の組の確率を合計する（設計書 15 の 8）。

    「予想が見た、このレースが 1,000倍以上で決まる確率」になる。荒れ具合の予想（レース単位の材料）とは別の材料
    （馬ごとの近走・適性）から作るので、2つを平均するとレース選びの精度が上がる。
    ``horses`` は今の予想の出走馬ごとの確率（1着の確率はレースで合計 1）、``odds`` は組 → 3連単のオッズ。
    オッズの無い組は 1,000倍未満とみなす（合計に入れない）。
    """

    def of(self, horses: RaceHorses, odds: Mapping[tuple[int, ...], float]) -> float:
        win = horses.win_of()
        return sum(trifecta_probability(win, *combo) for combo in permutations(horses.horse_numbers.tolist(), 3)
                   if odds.get(combo, 0.0) >= BIG_ODDS)
