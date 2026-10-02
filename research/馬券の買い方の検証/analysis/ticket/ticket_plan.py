"""買い方1つ。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import TicketType

from .breadth import Breadth
from .column_rule import ColumnRule


@dataclass(frozen=True)
class TicketPlan:
    """買い方1つ（券種・列の指定・広め/少点数・削る決まり）。目録は ``ticket_plans.py``。

    - ``name``: 人が読む名前（結果の表の見出し）。
    - ``rule_ids``: 元になったルール集の ID（docs/rules/馬券の買い方/）。
    - ``columns``: 列の指定。数は券種の馬の数と同じ。
    - ``breadth``: 広め（荒れるレース用）か少点数（自信のあるレース用）か。
    - ``odds_floor``: 確定オッズがこれ未満の買い目を削る（None なら削らない）。
    - ``excludes_dangerous``: 危険な人気馬（危険確率がしきい値以上）を候補から外す。
    - ``min_first_odds``: 1列目の先頭の馬の単勝オッズがこれ未満なら、そのレースは見送る（1倍台の本命を買わない）。
    - ``requires_top_favorite``: 本命（近走の1位）が 1番人気のレースだけ買う。
    """

    name: str
    rule_ids: tuple[str, ...]
    ticket_type: TicketType
    columns: tuple[ColumnRule, ...]
    breadth: Breadth
    odds_floor: float | None = None
    excludes_dangerous: bool = False
    min_first_odds: float | None = None
    requires_top_favorite: bool = False

    def __post_init__(self) -> None:
        expected = self.ticket_type.spec.horse_count
        if len(self.columns) != expected:
            raise ValueError(f"{self.name}: {self.ticket_type.label}の列は {expected}つです: {len(self.columns)}列")
