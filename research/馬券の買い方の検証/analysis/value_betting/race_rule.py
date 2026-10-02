"""戦略の軸「レースの選び方」。"""

from __future__ import annotations

from enum import Enum

from .protocol import RACES_PER_DAY


class RaceRule(Enum):
    """レースの選び方の2通り（docs/05-round3-protocol.md の「戦略の軸」）。値は保存の名前。

    - 全レース: 枠A（馬を選ぶ）だけ。
    - 1日3レースまで: 枠A のあと枠B（``DailyRaceCap``。平地の重賞は別枠）。
    """

    ALL = "all"
    CAP3 = "cap3"

    @property
    def label(self) -> str:
        """人が読む名前。"""
        return "全レース" if self is RaceRule.ALL else f"1日{RACES_PER_DAY}レースまで"

    @property
    def caps_per_day(self) -> bool:
        """枠B を使うか。"""
        return self is RaceRule.CAP3

    @classmethod
    def parse(cls, key: str) -> RaceRule:
        """保存の名前から。知らなければ ``ValueError``。"""
        for rule in cls:
            if rule.value == key:
                return rule
        raise ValueError(f"知らないレースの選び方です: {key}（{' / '.join(rule.value for rule in cls)}）")
