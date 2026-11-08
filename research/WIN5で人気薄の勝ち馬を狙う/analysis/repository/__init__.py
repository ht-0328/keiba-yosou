"""元DB を読むリポジトリ（1 SQL につき 1 クラス）。"""

from .runner_facts_repository import RunnerFactsRepository
from .win5_leg_repository import Win5LegRepository

__all__ = ["RunnerFactsRepository", "Win5LegRepository"]
