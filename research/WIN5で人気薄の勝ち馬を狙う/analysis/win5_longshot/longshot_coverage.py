"""買い目が、人気薄（10番人気以下）の勝ち馬をどれだけ含んでいたかを数える。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from yosou.form_aptitude_win5_tickets.formation import Formation
from yosou.form_aptitude_win5_tickets.repository.win5_columns import HORSE_NO
from yosou.form_aptitude_win5_tickets.settlement import Win5Outcome

from ..enrichment.race_market_shape import LONGSHOT_POPULARITY
from .upset_legs import popularity_of


@dataclass(frozen=True)
class LongshotCoverage:
    """（人気薄が勝ったレースの数, そのうち勝ち馬がどれかの買い目に入っていた数）。勝ち馬は当たり組の最初のもの（同着は1頭目）。"""

    def of(self, formations: Sequence[Formation], legs: Sequence[pd.DataFrame], outcome: Win5Outcome) -> tuple[int, int]:
        if not outcome.winners:
            return 0, 0
        combo = outcome.winners[0][0]
        flags = [self._leg(leg, index, number, formations) for index, (leg, number) in enumerate(zip(legs, combo, strict=True))]
        longshot = [covered for covered in flags if covered is not None]
        return len(longshot), sum(longshot)

    @staticmethod
    def _leg(leg: pd.DataFrame, index: int, winner: int, formations: Sequence[Formation]) -> bool | None:
        """人気薄が勝ったレースなら、勝ち馬がどれかの買い目に入っていたか。人気薄が勝っていなければ None。"""
        popularity = popularity_of(leg)
        found = popularity[leg[HORSE_NO].astype(int) == winner]
        if found.empty or float(found.iloc[0]) < LONGSHOT_POPULARITY:
            return None
        return any(winner in formation.legs[index] for formation in formations)
