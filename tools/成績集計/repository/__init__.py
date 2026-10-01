"""基準のページを数えるために元DB から読む部品。1つのクラスが1つの SQL を持つ。

事実表（``共通/facts.py`` の SQL）と成績の集計（``共通/perf.py``）は使わない。答え合わせの基準を、別の道筋で数えるためである。
"""

from .final_runner_repository import FinalRunnerRepository
from .mining_score_repository import MiningScoreRepository
from .payout_repository import PayoutRepository
from .pedigree_repository import PedigreeRepository

__all__ = ["FinalRunnerRepository", "MiningScoreRepository", "PayoutRepository", "PedigreeRepository"]
