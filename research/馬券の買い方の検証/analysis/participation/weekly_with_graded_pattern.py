"""⑥毎週参加し、重賞は必ず参加する。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import IS_GRADED, RACE_ID
from .confidence_judge import ConfidenceJudge
from .participation import BUY_NARROW, BUY_WIDE, Participation
from .pattern_needs import PatternNeeds
from .upset_judge import UpsetJudge
from .weekly_top_pattern import WeeklyTopPattern


class WeeklyWithGradedPattern:
    """⑥ ⑤（週ごとの上位 k）に、重賞を必ず足す。重賞は荒れ判定なら広め、そうでなければ少点数で買う。"""

    def __init__(self, inner: WeeklyTopPattern) -> None:
        self._inner = inner

    @property
    def key(self) -> str:
        return f"06week-graded-{self._inner.mode.value}"

    @property
    def label(self) -> str:
        return f"⑥毎週上位k + 重賞（{self._inner.mode.label}）"

    @property
    def needs(self) -> PatternNeeds:
        return self._inner.needs | PatternNeeds(upset=True, wide=True, narrow=True)

    def select(self, races: pd.DataFrame, upset: UpsetJudge, confidence: ConfidenceJudge, wide_bet: BetType,
               top_k: int | None) -> Participation:
        base = self._inner.select(races, upset, confidence, wide_bet, top_k).rows
        graded = races[IS_GRADED].fillna(False).to_numpy()
        is_upset = upset.is_upset(races, wide_bet).to_numpy()
        wide = base[BUY_WIDE].to_numpy() | (graded & is_upset)
        narrow = base[BUY_NARROW].to_numpy() | (graded & ~is_upset & ~wide)
        return Participation(races[RACE_ID], wide, narrow)
