"""1つの買い方を全レースに当てて精算する。"""

from __future__ import annotations

from 共通.perf import STAKE_YEN

from ..race_material import RaceMaterials
from ..ticket import DangerousFavoriteFilter, Ticket, TicketBuilder, TicketPlan
from .odds_floor_cut import OddsFloorCut
from .payout_book import PayoutBook
from .plan_result import PlanResult

#: 見送りの理由（買い目を作る前後に決まるもの。買い目を作れない理由は ``TicketBuilder`` が出す）。
SKIP_NO_PAYOUT = "払戻データなし"
SKIP_VOID = "不成立"
SKIP_NO_ODDS = "オッズなし（カットできない）"
SKIP_NOTHING_LEFT = "カット後に買い目なし"


class PlanSettler:
    """1つの買い方を、材料表の全レースに当てて、レースごとの ``PlanResult`` にする。

    レースごとに: 払戻データの有無 → その券種の不成立 → 買い目を作る（``TicketBuilder``）→ 低配当目のカット →
    払戻との照合。賭け金は 1点 ``STAKE_YEN``（100円）。
    """

    def __init__(self, plan: TicketPlan, materials: RaceMaterials, payout_book: PayoutBook, odds_cut: OddsFloorCut,
                 dangerous_filter: DangerousFavoriteFilter | None = None) -> None:
        self._plan = plan
        self._materials = materials
        self._payout_book = payout_book
        self._odds_cut = odds_cut
        self._builder = TicketBuilder(plan, dangerous_filter)

    def settle_all(self) -> list[PlanResult]:
        return [self._settle(race_id) for race_id in self._materials.race_ids]

    def _settle(self, race_id: str) -> PlanResult:
        skipped = self._precheck(race_id)
        if skipped is not None:
            return PlanResult.skip(race_id, self._plan.name, skipped)
        built = self._builder.build(self._materials.runners_of(race_id))
        if built.skipped is not None:
            return PlanResult.skip(race_id, self._plan.name, built.skipped)
        tickets = self._cut(race_id, list(built.tickets))
        if tickets is None:
            return PlanResult.skip(race_id, self._plan.name, SKIP_NO_ODDS)
        if not tickets:
            return PlanResult.skip(race_id, self._plan.name, SKIP_NOTHING_LEFT)
        return self._result(race_id, tickets)

    def _precheck(self, race_id: str) -> str | None:
        if not self._payout_book.has_race(race_id):
            return SKIP_NO_PAYOUT
        if self._payout_book.is_void(race_id, self._plan.ticket_type):
            return SKIP_VOID
        return None

    def _cut(self, race_id: str, tickets: list[Ticket]) -> list[Ticket] | None:
        """低配当目のカット（買い方に下限があるときだけ）。"""
        if self._plan.odds_floor is None:
            return tickets
        return self._odds_cut.apply(race_id, tickets, self._plan.odds_floor)

    def _result(self, race_id: str, tickets: list[Ticket]) -> PlanResult:
        payouts = [self._payout_book.payout_yen(race_id, ticket) for ticket in tickets]
        hits = sum(1 for yen in payouts if yen > 0)
        return PlanResult(race_id, self._plan.name, len(tickets), len(tickets) * STAKE_YEN, sum(payouts), hits)
