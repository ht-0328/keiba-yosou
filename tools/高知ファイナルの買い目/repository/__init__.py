"""元DB から読む部品。"""

from .final_race_repository import FinalRaceRepository
from .kochi_run_repository import KochiRunRepository

__all__ = ["FinalRaceRepository", "KochiRunRepository"]
