"""元DB を読むリポジトリ（1 SQL につき 1 クラス）。確定オッズのリポジトリ（券種・3連単）は本番の道具 tools/地方の推奨買目 に移した。"""

from 地方の推奨買目.repository import LocalTicketOddsRepository, TrifectaOddsRepository

from .facts_repository import FactsRepository
from .horse_area_repository import HorseAreaRepository
from .ticket_payout_repository import LocalTicketPayoutRepository
from .trainer_area_repository import TrainerAreaRepository
from .trifecta_payout_repository import TrifectaPayoutRepository
from .trifecta_result_repository import TrifectaResultRepository
from .trio_odds_repository import TrioOddsRepository
from .trio_result_repository import TrioResultRepository

__all__ = ["FactsRepository", "HorseAreaRepository", "LocalTicketOddsRepository", "LocalTicketPayoutRepository", "TrainerAreaRepository",
           "TrifectaOddsRepository", "TrifectaPayoutRepository", "TrifectaResultRepository", "TrioOddsRepository", "TrioResultRepository"]
