"""出どころごとの判定の集まり。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .source_adoption_rule import SourceVerdict


@dataclass(frozen=True)
class SourceVerdicts:
    """元以外の出どころの名前 → 判定。"""

    by_source: Mapping[str, SourceVerdict]

    def of(self, source: str) -> SourceVerdict:
        """その出どころの判定。無ければ ``KeyError``。"""
        return self.by_source[source]

    @property
    def any_better(self) -> bool:
        """元より良い出どころが1つでもあるか。"""
        return any(verdict.better_than_original for verdict in self.by_source.values())
