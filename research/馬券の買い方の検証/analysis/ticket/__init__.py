"""買い方（券種・列の指定・候補の選び方）から、1レースの買い目を作る。

| クラス | 仕事 |
|---|---|
| ``Ticket`` | 買い目1つ（券種と馬番の組。順不同は昇順にそろえる）。``combo`` は払戻の組番と同じ形 |
| ``FormationTickets`` | 列ごとの馬番の並びから買い目を作る（直積・同じ馬を除く・順不同は1つに） |
| ``ColumnRule`` | 1列の指定（候補の選び方・頭数・前の列を含めるか・先の列の写しか） |
| ``TicketPlan`` | 買い方1つ（名前・ルール ID・券種・列の並び・広め/少点数・削る決まり）。目録は ``ticket_plans.py`` |
| ``PlanTickets`` | 1レース × 1買い方の買い目（か、見送った理由） |
| ``TicketBuilder`` | 1レースの runners と ``TicketPlan`` から買い目を作る |
| ``DangerousFavoriteFilter`` | 危険確率がしきい値以上の人気馬を候補から外す |
| ``Breadth`` | 広め・少点数 |
| ``picker/`` | 候補の選び方（近走の順・穴馬の順・人気順位 …） |

券種（``TicketType``）は共通の ``yosou.shared.betting`` のものを使う。
``upset_bet_of(券種)`` は、その券種の買い方でどの券種の荒れ具合を見るかの対応（複勝 → 単勝、ワイド・馬単 → 馬連）。
"""

from .breadth import Breadth
from .column_rule import ColumnRule
from .dangerous_favorite_filter import DANGEROUS_THRESHOLD, DangerousFavoriteFilter
from .formation_tickets import FormationTickets
from .plan_tickets import PlanTickets
from .ticket import Ticket
from .ticket_builder import SKIP_LOW_ODDS, SKIP_NO_CANDIDATES, SKIP_TOP_NOT_FAVORITE, TicketBuilder
from .ticket_plan import TicketPlan
from .ticket_plans import (
    ALL_NARROW_PLANS,
    ALL_PLANS,
    ALL_WIDE_PLANS,
    BASELINE_PLANS,
    NARROW_PLANS,
    VALUE_NARROW_PLANS,
    VALUE_WIDE_PLANS,
    WIDE_PLANS,
    plan_named,
)
from .upset_bet_of import upset_bet_of

__all__ = [
    "Ticket", "FormationTickets", "ColumnRule",
    "TicketPlan", "PlanTickets", "TicketBuilder", "DangerousFavoriteFilter", "DANGEROUS_THRESHOLD", "Breadth",
    "ALL_PLANS", "NARROW_PLANS", "WIDE_PLANS", "VALUE_NARROW_PLANS", "VALUE_WIDE_PLANS", "ALL_NARROW_PLANS", "ALL_WIDE_PLANS",
    "BASELINE_PLANS", "plan_named", "upset_bet_of",
    "SKIP_NO_CANDIDATES", "SKIP_TOP_NOT_FAVORITE", "SKIP_LOW_ODDS",
]
