"""戦略1つ（馬の選び方 × 線 × レースの選び方）。"""

from __future__ import annotations

from dataclasses import dataclass

from .horse_selection import HorseSelection
from .line_rule import LineRule
from .race_rule import RaceRule

#: 保存の名前の区切り。
_SEPARATOR = "|"


@dataclass(frozen=True)
class Round3Strategy:
    """3回目の戦略1つ。券種は複勝だけ、1レース最大3点・1点 100円は固定なので、軸の3つだけを持つ。"""

    selection: HorseSelection
    line_rule: LineRule
    race_rule: RaceRule

    @property
    def key(self) -> str:
        """保存の名前（例 ``mid|chosen|all``）。"""
        return _SEPARATOR.join((self.selection.value, self.line_rule.value, self.race_rule.value))

    @property
    def name(self) -> str:
        """人が読む名前（例 中穴だけ・線を選ぶ・全レース）。"""
        return "・".join((self.selection.label, self.line_rule.label, self.race_rule.label))

    def to_dict(self) -> dict[str, str]:
        return {"selection": self.selection.value, "line_rule": self.line_rule.value, "race_rule": self.race_rule.value}

    @classmethod
    def from_dict(cls, saved: dict[str, str]) -> Round3Strategy:
        return cls(HorseSelection.parse(saved["selection"]), LineRule.parse(saved["line_rule"]), RaceRule.parse(saved["race_rule"]))

    @classmethod
    def from_key(cls, key: str) -> Round3Strategy:
        """保存の名前から。形が違えば ``ValueError``。"""
        parts = key.split(_SEPARATOR)
        if len(parts) != 3:
            raise ValueError(f"戦略の名前は「馬の選び方|線|レースの選び方」の形です: {key}")
        return cls(HorseSelection.parse(parts[0]), LineRule.parse(parts[1]), RaceRule.parse(parts[2]))
