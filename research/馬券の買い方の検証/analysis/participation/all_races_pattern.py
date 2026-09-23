"""①全レースに参加する。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import RACE_ID
from ..ticket import Breadth
from .confidence_judge import ConfidenceJudge
from .participation import Participation
from .pattern_needs import PatternNeeds
from .upset_judge import UpsetJudge


class AllRacesPattern:
    """①全レースを買う。``fixed`` が None なら、荒れ判定のレースは広め、そうでなければ少点数で買う。

    ``fixed`` に広めか少点数を渡すと、全レースをその買い方だけで買う（切り替えの効き目を見る比較用）。
    """

    def __init__(self, fixed: Breadth | None = None) -> None:
        self._fixed = fixed

    @property
    def key(self) -> str:
        return {None: "01all", Breadth.WIDE: "01all-wide", Breadth.NARROW: "01all-narrow"}[self._fixed]

    @property
    def label(self) -> str:
        return {None: "①全レース（荒れなら広め、ほかは少点数）", Breadth.WIDE: "①全レース（広め固定）",
                Breadth.NARROW: "①全レース（少点数固定）"}[self._fixed]

    @property
    def needs(self) -> PatternNeeds:
        if self._fixed is None:
            return PatternNeeds(upset=True, wide=True, narrow=True)
        return PatternNeeds(wide=self._fixed is Breadth.WIDE, narrow=self._fixed is Breadth.NARROW)

    def select(self, races: pd.DataFrame, upset: UpsetJudge, confidence: ConfidenceJudge, wide_bet: BetType,
               top_k: int | None) -> Participation:
        everyone = pd.Series(True, index=races.index)
        if self._fixed is Breadth.WIDE:
            return Participation(races[RACE_ID], everyone, ~everyone)
        if self._fixed is Breadth.NARROW:
            return Participation(races[RACE_ID], ~everyone, everyone)
        is_upset = upset.is_upset(races, wide_bet)
        return Participation(races[RACE_ID], is_upset, ~is_upset)
