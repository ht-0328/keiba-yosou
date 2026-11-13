"""対象レースの馬を、買い目に入れる順に並べる決まり。"""

from __future__ import annotations

from enum import Enum

import pandas as pd

from yosou.shared.dataset import HORSE_NO

from ..leg import EDGE, SHARE


class LegOrdering(Enum):
    """各レースで、上から何頭選ぶときの馬の順（設計書 15 の 5、16 の 4.）。

    - 上乗せの順: そろえた1着の確率 ÷ オッズから見た勝率 の大きい順（市場より高く見ている馬から）。同じなら1着の確率の大きい順。
    - 1着の確率の順: そろえた1着の確率の大きい順。
    どちらも、最後は馬番の小さい順で並びを決める。
    """

    BY_EDGE = "上乗せの順"
    BY_PROBABILITY = "1着の確率の順"

    @property
    def label(self) -> str:
        return self.value

    @classmethod
    def parse(cls, text: str) -> LegOrdering:
        """``上乗せの順``・``上乗せ``・``1着の確率の順``・``1着の確率`` か、英語の名前（``by_edge`` など）から。知らなければ ``ValueError``。"""
        found = _BY_TEXT.get(text.strip())
        if found is None:
            names = " / ".join(each.label for each in cls)
            raise ValueError(f"知らない並べ方です: {text}（{names}）")
        return found

    def order(self, leg: pd.DataFrame) -> pd.DataFrame:
        """1レースの確率の表（``RaceWinShare`` の結果）を、この順に並べ直した表（index は 0 から振り直す）。"""
        keys = [EDGE, SHARE, HORSE_NO] if self is LegOrdering.BY_EDGE else [SHARE, HORSE_NO]
        ascending = [False] * (len(keys) - 1) + [True]
        return leg.sort_values(keys, ascending=ascending, kind="stable").reset_index(drop=True)


_BY_TEXT: dict[str, LegOrdering] = {
    "上乗せの順": LegOrdering.BY_EDGE, "上乗せ": LegOrdering.BY_EDGE, "by_edge": LegOrdering.BY_EDGE,
    "1着の確率の順": LegOrdering.BY_PROBABILITY, "1着の確率": LegOrdering.BY_PROBABILITY, "by_probability": LegOrdering.BY_PROBABILITY,
}
