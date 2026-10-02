"""戦略の軸「線」。"""

from __future__ import annotations

from enum import Enum

from .protocol import FIXED_LINE


class LineRule(Enum):
    """期待値の線の決め方の2通り（docs/05-round3-protocol.md の「戦略の軸」）。値は保存の名前。

    - 選ぶ: 区切りごとに直前の1年で決める（``ValidationLineChooser``）。決まらなければその区切りは買わない。
    - 固定: 設計書の値（1.25）をどの区切りでも使う。
    """

    CHOSEN = "chosen"
    FIXED = "fixed"

    @property
    def label(self) -> str:
        """人が読む名前。"""
        return "線を選ぶ" if self is LineRule.CHOSEN else f"{FIXED_LINE:g} 固定"

    @classmethod
    def parse(cls, key: str) -> LineRule:
        """保存の名前から。知らなければ ``ValueError``。"""
        for rule in cls:
            if rule.value == key:
                return rule
        raise ValueError(f"知らない線の決め方です: {key}（{' / '.join(rule.value for rule in cls)}）")
