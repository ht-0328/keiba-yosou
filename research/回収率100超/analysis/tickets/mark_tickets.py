"""印のルールから、券種ごとの買い目を作る。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import numpy as np
import pandas as pd

from .ticket_kind import KINDS_BY_KEY


@dataclass(frozen=True)
class MarkRule:
    """1つの印のルール。``columns`` は組の1頭目・2頭目・3頭目に置く印（券種の馬の数だけ）。"""

    kind_key: str
    columns: tuple[tuple[str, ...], ...]
    stake_units: float
    variant: str


#: 設計書「買うレースと買い目を決める」の 08 の 2 の表。1点の額は単位（勝負レースの予算 ÷ 3）で数える。
MARK_RULES: tuple[MarkRule, ...] = (
    MarkRule("win", (("◎",),), 1.0, "通常"),
    MarkRule("wide", (("◎",), ("☆", "注")), 1.0, "通常"),
    MarkRule("quinella", (("◎",), ("○", "▲", "☆")), 0.5, "通常"),
    MarkRule("trio", (("◎",), ("○", "▲", "☆"), ("○", "▲", "△1", "△2", "☆")), 0.3, "通常"),
    MarkRule("trio", (("☆",), ("◎", "○", "▲"), ("◎", "○", "▲", "△1", "△2", "注")), 0.2, "荒れそう"),
)


class MarkTickets:
    """印の表（1行 = 1レース）から、ルールごとの買い目を作る。

    同じ馬が2回入る組と、順不同の券種で並びだけが違う組は1点にまとめる。
    例: 3連複の ◎−○−▲ と ◎−▲−○ は同じ1点。
    出力の列: kind・variant・rid・flat・stake_units。
    """

    def build(self, marks: pd.DataFrame) -> pd.DataFrame:
        frames = [self._for_rule(marks, rule) for rule in MARK_RULES]
        return pd.concat(frames, ignore_index=True)

    def _for_rule(self, marks: pd.DataFrame, rule: MarkRule) -> pd.DataFrame:
        kind = KINDS_BY_KEY[rule.kind_key]
        combos = [self._race_combos(row, rule, kind.ordered) for row in marks.to_dict("records")]
        rows = [(rid, combo) for rid, found in zip(marks["rid"], combos, strict=True) for combo in found]
        if not rows:
            return pd.DataFrame(columns=["kind", "variant", "rid", "flat", "stake_units"])
        rid, horses = zip(*rows, strict=True)
        return pd.DataFrame({"kind": rule.kind_key, "variant": rule.variant, "rid": np.array(rid),
                             "flat": kind.flat_index(np.array(horses)), "stake_units": rule.stake_units})

    def _race_combos(self, marked: dict, rule: MarkRule, ordered: bool) -> list[tuple[int, ...]]:
        choices = [[marked[mark] for mark in position if pd.notna(marked[mark])] for position in rule.columns]
        combos = {self._normalize(combo, ordered) for combo in product(*choices)}
        return sorted(combo for combo in combos if len(set(combo)) == len(combo))

    def _normalize(self, combo: tuple, ordered: bool) -> tuple[int, ...]:
        numbers = tuple(int(horse) for horse in combo)
        return numbers if ordered else tuple(sorted(numbers))
