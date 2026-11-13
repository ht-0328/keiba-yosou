"""WIN5 の1日の5レースのうち、荒れそうなレース（R1 人気薄に票が残る か R3 ハンデ戦）を、人気薄の市場合計の大きい順に返す。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from yosou.form_aptitude_win5_tickets.leg import MARKET
from yosou.form_aptitude_win5_tickets.repository.win5_columns import RACE_ID, WIN_ODDS

from ..enrichment.race_market_shape import LONGSHOT_POPULARITY
from ..theory.race_type_catalog import LONGSHOT_SHARE


def popularity_of(leg: pd.DataFrame) -> pd.Series:
    """レースの確率の表の各馬の人気（単勝オッズの小さい順。同じなら表の並び）。"""
    return leg[WIN_ODDS].rank(method="first")


@dataclass(frozen=True)
class UpsetLegs:
    """``handicap`` はハンデ戦のレースID の集まり。"""

    handicap: frozenset[str]

    def of(self, legs: Sequence[pd.DataFrame]) -> list[int]:
        """荒れそうなレースの位置（0〜4）を、人気薄の市場合計の大きい順に。"""
        shares = [self.longshot_share(leg) for leg in legs]
        upset = [index for index, leg in enumerate(legs) if self._is_upset(leg, shares[index])]
        return sorted(upset, key=lambda index: -shares[index])

    @staticmethod
    def longshot_share(leg: pd.DataFrame) -> float:
        """10番人気以下のオッズから見た勝率の合計。"""
        return float(leg.loc[popularity_of(leg) >= LONGSHOT_POPULARITY, MARKET].sum())

    def _is_upset(self, leg: pd.DataFrame, share: float) -> bool:
        return share >= LONGSHOT_SHARE or str(leg[RACE_ID].iloc[0]) in self.handicap
