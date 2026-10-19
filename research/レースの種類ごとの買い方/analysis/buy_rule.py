"""組の期待値で組を選ぶ決まり1つと、券種ごとの決まりの候補。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from yosou.shared.betting import TicketType

#: 対象（docs/01 の 4）。全レース・期待度「高」・◎ を含む組・期待度「高」で ◎ を含む組。
SCOPES: tuple[str, ...] = ("全", "高", "◎", "高◎")
#: 線（組の期待値）の候補。
LINES: tuple[float, ...] = (1.0, 1.1, 1.2, 1.3, 1.5)
#: 券種ごとのオッズの上限の候補。
CAPS: dict[TicketType, tuple[float, ...]] = {
    TicketType.WIN: (5, 10, 30, 50), TicketType.PLACE: (3, 5, 10, 30, 200),
    TicketType.WIDE: (30, 100, 300), TicketType.QUINELLA: (30, 100, 300, 1000), TicketType.EXACTA: (30, 100, 300, 1000),
    TicketType.TRIO: (100, 300, 1000, 3000), TicketType.TRIFECTA: (300, 1000, 3000, 10000),
}
#: 券種ごとの線の候補（無い券種は ``LINES``）。複勝は今の本番の線 1.25 も入れる（docs/04 の 2）。
LINES_OF: dict[TicketType, tuple[float, ...]] = {TicketType.PLACE: (1.0, 1.1, 1.2, 1.25, 1.3, 1.5)}
#: 1レースの点数の上限の候補（0 は上限なし）。
POINTS: tuple[int, ...] = (1, 3, 5, 0)


@dataclass(frozen=True)
class BuyRule:
    """対象 ``scope`` の組のうち、組の期待値が ``line`` 以上でオッズが ``cap`` 倍以下の組を、1レースで期待値の高い順に ``points`` 点まで買う（0 は全部）。

    例: ``BuyRule("高", 1.0, 300, 3)`` は今の本番のワイド（期待度「高」のレース・期待値 1.0 以上・300倍以下・3点まで）。
    """

    scope: str
    line: float
    cap: float
    points: int

    @property
    def text(self) -> str:
        """人が読む決まり。例: ``高・1.0・300倍・3点``。"""
        points = f"{self.points}点" if self.points else "点数の上限なし"
        return f"{self.scope}・{self.line:.1f}・{self.cap:,.0f}倍・{points}"


def rules_of(ticket_type: TicketType) -> tuple[BuyRule, ...]:
    """その券種の決まりの候補（対象 × 線 × 上限 × 点数）。"""
    return tuple(BuyRule(*values) for values in product(SCOPES, LINES_OF.get(ticket_type, LINES), CAPS[ticket_type], POINTS))


#: 今の本番の決まり（``tools/今週の予想/ticket_rules.py`` の ``COMBO_VALUE_RULES`` を、この研究の形にしたもの）。
CURRENT_RULES: dict[TicketType, BuyRule] = {
    TicketType.QUINELLA: BuyRule("全", 1.1, 100, 0), TicketType.EXACTA: BuyRule("全", 1.1, 30, 0),
    TicketType.WIDE: BuyRule("高", 1.0, 300, 3), TicketType.TRIO: BuyRule("◎", 1.2, 1000, 3),
    TicketType.TRIFECTA: BuyRule("全", 1.3, 3000, 0),
}
