"""券種ごとの、買い目の作り方・点数の上限・賭け金の決め方。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol

from yosou.shared.betting import TicketType

from .combo_groups import POPULAR_POPULAR
from .pair_combos import PairCombos
from .race_horses import RaceHorses
from .single_combos import SingleCombos
from .trifecta_combos import TrifectaCombos
from .trio_combos import TrioCombos


class Combos(Protocol):
    def of(self, horses: RaceHorses, upset: bool) -> list[tuple[tuple[int, ...], str]]: ...


@dataclass(frozen=True)
class TicketSpec:
    """1つの券種の買い方。

    - ``combos``: 買い目の候補の作り方。候補のうち期待値が 1 以上のものを、期待値の高い順に ``max_points`` 点まで買う
      （荒れそうなレースでは ``upset_max_points`` 点まで）。``group_limits`` は組み合わせの種類ごとの上限（人気-人気は1点）。
    - 賭け金: ``stake_per_point`` があれば1点その金額（3連単 100円・3連複 300円）。無ければ、券種の予算 ``budget`` を
      払戻均等（どれが当たっても払戻がほぼ同じになるよう、オッズの低い買い目ほど多く）で分ける。どれも 100円単位。
    """

    ticket: TicketType
    combos: Combos
    max_points: int
    upset_max_points: int
    stake_per_point: int | None = None
    budget: int | None = None
    group_limits: Mapping[str, int] = field(default_factory=dict)

    def points_for(self, upset: bool) -> int:
        return self.upset_max_points if upset else self.max_points


_PAIR_LIMITS = {POPULAR_POPULAR: 1}

#: 1レースの予算（円）。券種は期待値の高い順に、この予算に入るところまで買う。
RACE_BUDGET = 5000

#: 券種ごとの買い方（利用者と決めたもの。3連単は 100円で広め、3連複は 300円ほど）。
TICKET_SPECS: tuple[TicketSpec, ...] = (
    TicketSpec(TicketType.WIN, SingleCombos(), 2, 2, budget=1500),
    TicketSpec(TicketType.PLACE, SingleCombos(), 2, 2, budget=1000),
    TicketSpec(TicketType.QUINELLA, PairCombos(ordered=False), 5, 8, budget=1000, group_limits=_PAIR_LIMITS),
    TicketSpec(TicketType.WIDE, PairCombos(ordered=False), 5, 8, budget=1000, group_limits=_PAIR_LIMITS),
    TicketSpec(TicketType.EXACTA, PairCombos(ordered=True), 5, 8, budget=1000, group_limits=_PAIR_LIMITS),
    TicketSpec(TicketType.TRIO, TrioCombos(), 8, 10, stake_per_point=300),
    TicketSpec(TicketType.TRIFECTA, TrifectaCombos(), 30, 30, stake_per_point=100),
)
