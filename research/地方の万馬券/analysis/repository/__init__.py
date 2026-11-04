"""元DB を読むリポジトリ（1 SQL につき 1 クラス）。"""

from .facts_repository import FactsRepository
from .horse_area_repository import HorseAreaRepository
from .ticket_odds_repository import LocalTicketOddsRepository
from .ticket_payout_repository import LocalTicketPayoutRepository
from .trainer_area_repository import TrainerAreaRepository
from .trifecta_odds_repository import TrifectaOddsRepository
from .trifecta_payout_repository import TrifectaPayoutRepository
from .trifecta_result_repository import TrifectaResultRepository
from .trio_odds_repository import TrioOddsRepository
from .trio_result_repository import TrioResultRepository

__all__ = ["FactsRepository", "HorseAreaRepository", "LocalTicketOddsRepository", "LocalTicketPayoutRepository", "TrainerAreaRepository",
           "TrifectaOddsRepository", "TrifectaPayoutRepository", "TrifectaResultRepository", "TrioOddsRepository", "TrioResultRepository"]
