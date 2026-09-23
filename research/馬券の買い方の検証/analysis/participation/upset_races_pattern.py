"""②荒れるレースだけに参加する。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import RACE_ID
from .confidence_judge import ConfidenceJudge
from .participation import Participation
from .pattern_needs import PatternNeeds
from .upset_judge import UpsetJudge


class UpsetRacesPattern:
    """②荒れ判定のレースだけを、広めで買う。"""

    key = "02upset"
    label = "②荒れるレースだけ（広め）"
    needs = PatternNeeds(upset=True, wide=True)

    def select(self, races: pd.DataFrame, upset: UpsetJudge, confidence: ConfidenceJudge, wide_bet: BetType,
               top_k: int | None) -> Participation:
        is_upset = upset.is_upset(races, wide_bet)
        return Participation(races[RACE_ID], is_upset, pd.Series(False, index=races.index))
