"""③自信のあるレースだけに参加する。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import RACE_ID
from .confidence_judge import ConfidenceJudge
from .participation import Participation
from .pattern_needs import PatternNeeds
from .upset_judge import UpsetJudge


class ConfidentRacesPattern:
    """③自信ありのレースだけを、少点数で買う。"""

    key = "03conf"
    label = "③自信のあるレースだけ（少点数）"
    needs = PatternNeeds(form=True, danger=True, narrow=True)

    def select(self, races: pd.DataFrame, upset: UpsetJudge, confidence: ConfidenceJudge, wide_bet: BetType,
               top_k: int | None) -> Participation:
        is_confident = confidence.is_confident(races)
        return Participation(races[RACE_ID], pd.Series(False, index=races.index), is_confident)
