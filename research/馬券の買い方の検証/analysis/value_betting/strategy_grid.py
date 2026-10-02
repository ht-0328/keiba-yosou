"""探索で回す戦略の並び（3 × 2 × 2 = 12）。"""

from __future__ import annotations

from .horse_selection import HorseSelection
from .line_rule import LineRule
from .race_rule import RaceRule
from .strategy import Round3Strategy

#: 全部の戦略（馬の選び方 → 線 → レースの選び方 の順）。
STRATEGIES: tuple[Round3Strategy, ...] = tuple(
    Round3Strategy(selection, line_rule, race_rule)
    for selection in HorseSelection for line_rule in LineRule for race_rule in RaceRule
)


def strategy_keyed(key: str) -> Round3Strategy:
    """保存の名前から戦略を引く。並びに無ければ ``ValueError``。"""
    for strategy in STRATEGIES:
        if strategy.key == key:
            return strategy
    raise ValueError(f"知らない戦略です: {key}（{' / '.join(strategy.key for strategy in STRATEGIES)}）")
