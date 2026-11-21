"""元DB を読むリポジトリ（1 SQL につき 1 クラス）。3連単の払戻は研究「地方の万馬券」のリポジトリを使う。"""

from 地方の万馬券.analysis.repository import TrifectaPayoutRepository

from .kochi_runs_repository import KochiRunsRepository

__all__ = ["KochiRunsRepository", "TrifectaPayoutRepository"]
