"""④荒れるレースと自信のあるレースの両方に参加する。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import RACE_ID
from .confidence_judge import ConfidenceJudge
from .participation import Participation
from .pattern_needs import PatternNeeds
from .upset_judge import UpsetJudge


class UnionPattern:
    """④荒れ判定のレースは広めで、自信ありのレースは少点数で買う（両方に当たるレースは両方買う）。"""

    key = "04union"
    label = "④荒れる（広め）と自信（少点数）の両方"
    needs = PatternNeeds(upset=True, form=True, danger=True, wide=True, narrow=True)

    def select(self, races: pd.DataFrame, upset: UpsetJudge, confidence: ConfidenceJudge, wide_bet: BetType,
               top_k: int | None) -> Participation:
        return Participation(races[RACE_ID], upset.is_upset(races, wide_bet), confidence.is_confident(races))
