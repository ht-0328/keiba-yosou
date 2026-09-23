"""⑤毎週、上位のレースを選んで参加する。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import RACE_ID, WEEK
from .confidence_judge import ConfidenceJudge
from .participation import Participation
from .pattern_needs import PatternNeeds
from .upset_judge import UpsetJudge
from .weekly_mode import WeeklyMode


class WeeklyTopPattern:
    """⑤週ごとに、荒れ度の高い順（広め）か自信の高い順（少点数）か両方で、上位 k レースを買う。

    しきい値は使わず順位で選ぶので、毎週必ず参加する（点の無いレース = 荒れ具合の予測が無い・危険の条件を満たさない、は選ばない）。
    """

    def __init__(self, mode: WeeklyMode) -> None:
        self._mode = mode

    @property
    def mode(self) -> WeeklyMode:
        return self._mode

    @property
    def key(self) -> str:
        return f"05week-{self._mode.value}"

    @property
    def label(self) -> str:
        return f"⑤毎週上位k（{self._mode.label}）"

    @property
    def needs(self) -> PatternNeeds:
        return PatternNeeds(
            danger=self._mode.uses_confidence, top_k=True, wide=self._mode.uses_upset, narrow=self._mode.uses_confidence,
        )

    def select(self, races: pd.DataFrame, upset: UpsetJudge, confidence: ConfidenceJudge, wide_bet: BetType,
               top_k: int | None) -> Participation:
        if top_k is None:
            raise ValueError("毎週のパターンには週の上位 k が要ります")
        nobody = pd.Series(False, index=races.index)
        wide = self._top(races, upset.scores(races, wide_bet), top_k) if self._mode.uses_upset else nobody
        narrow = self._top(races, confidence.scores(races), top_k) if self._mode.uses_confidence else nobody
        return Participation(races[RACE_ID], wide, narrow)

    def _top(self, races: pd.DataFrame, scores: pd.Series, top_k: int) -> pd.Series:
        """週ごとに点の高い上位 k（点の無いレースは選ばない）。"""
        ranks = scores.groupby(races[WEEK]).rank(ascending=False, method="first")
        return (ranks <= top_k).fillna(False) & scores.notna()
