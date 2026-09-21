"""終わった1レース（条件・レースの行・結果）。"""

from __future__ import annotations

from dataclasses import dataclass

from .race_outcome import RaceOutcome
from .race_plan import RacePlan


@dataclass(frozen=True)
class FinishedRace:
    """終わった1レース。``row`` は合成DB のレースの行、``outcome`` は結果。"""

    plan: RacePlan
    row: dict[str, str]
    outcome: RaceOutcome
