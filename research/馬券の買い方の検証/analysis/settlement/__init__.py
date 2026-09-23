"""買い目を払戻と照合し、レース × 買い方 の精算表を作る。

| クラス | 仕事 |
|---|---|
| ``PayoutBook`` | (レースID, 券種, 組番) → 払戻円。券種ごとの不成立と、払戻データの有無も答える |
| ``OddsBook`` | (レースID, 券種, 組番) → 確定オッズ |
| ``OddsFloorCut`` | 確定オッズが下限未満の買い目を落とす（オッズの無いレースは判定不能） |
| ``PlanResult`` | 1レース × 1買い方の結果（点数・賭け金・払戻・的中数・見送りの理由） |
| ``PlanSettler`` | 1つの買い方を全レースに当てて ``PlanResult`` の並びにする |
| ``SettlementTable`` | 全買い方 × 全レースの精算表（DataFrame）。CSV に保存・読み戻し |
"""

from .odds_book import OddsBook
from .odds_floor_cut import OddsFloorCut
from .payout_book import PayoutBook
from .plan_result import PlanResult
from .plan_settler import SKIP_NO_ODDS, SKIP_NO_PAYOUT, SKIP_NOTHING_LEFT, SKIP_VOID, PlanSettler
from .settlement_table import SettlementTable

__all__ = [
    "PayoutBook", "OddsBook", "OddsFloorCut", "PlanResult", "PlanSettler", "SettlementTable",
    "SKIP_NO_PAYOUT", "SKIP_VOID", "SKIP_NO_ODDS", "SKIP_NOTHING_LEFT",
]
