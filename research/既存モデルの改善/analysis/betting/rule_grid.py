"""券種ごとの買い方の候補の並び。"""

from __future__ import annotations

from itertools import product

from 馬券の買い方の検証.analysis.ticket import TicketType

from .betting_rule import BettingRule

#: 期待値の線の候補（どの券種も同じ）。
_VALUES: tuple[float, ...] = (1.0, 1.1, 1.2, 1.3, 1.5, 2.0)
#: 券種ごとの、オッズの上限の候補と、1レースの点数の上限の候補。
_ODDS_CAPS: dict[TicketType, tuple[float, ...]] = {
    TicketType.WIN: (10.0, 20.0, 50.0, 200.0),
    TicketType.PLACE: (3.0, 5.0, 10.0, 50.0),
    TicketType.QUINELLA: (30.0, 100.0, 300.0, 1000.0),
    TicketType.WIDE: (10.0, 30.0, 100.0, 300.0),
    TicketType.EXACTA: (50.0, 200.0, 500.0, 2000.0),
    TicketType.TRIO: (100.0, 300.0, 1000.0, 5000.0),
    TicketType.TRIFECTA: (300.0, 1000.0, 5000.0, 20000.0),
}
_PER_RACE: dict[TicketType, tuple[int, ...]] = {
    TicketType.WIN: (1, 2), TicketType.PLACE: (1, 2, 3),
    TicketType.QUINELLA: (1, 3, 5), TicketType.WIDE: (1, 3, 5), TicketType.EXACTA: (1, 3, 5),
    TicketType.TRIO: (1, 3, 5, 10), TicketType.TRIFECTA: (1, 3, 5, 10),
}


def _rules_of(ticket_type: TicketType) -> tuple[BettingRule, ...]:
    combinations = product(_VALUES, _ODDS_CAPS[ticket_type], _PER_RACE[ticket_type])
    return tuple(BettingRule(ticket_type, value, cap, count) for value, cap, count in combinations)


#: 券種 → 買い方の候補。検証期間の回収率で、この中から1つ選ぶ（``RuleChooser``）。
RULE_GRID: dict[TicketType, tuple[BettingRule, ...]] = {ticket_type: _rules_of(ticket_type) for ticket_type in TicketType}
#: 候補を作るときに落とす下限の期待値と、券種ごとのオッズの上限（候補の表を小さくする）。
MIN_VALUE = min(_VALUES)
MAX_ODDS: dict[TicketType, float] = {ticket_type: max(caps) for ticket_type, caps in _ODDS_CAPS.items()}
