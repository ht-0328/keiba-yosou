"""券種ごとの、買うレースの絞り方1つ（docs/03 の 2 の仮説）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.betting import TicketType


@dataclass(frozen=True)
class RaceFilter:
    """レースの中身 ``trait`` が ``low`` 以上 ``high`` 以下のレースだけ買う絞り方（None の端は区切らない）。``text`` は人が読む名前。

    例: ``RaceFilter("favorite_odds", 2.9, None, "1番人気が 2.9倍以上")`` は、1番人気の単勝オッズが 2.9倍以上のレースだけ。
    """

    trait: str
    low: float | None
    high: float | None
    text: str

    def passes(self, traits: pd.DataFrame) -> pd.Series:
        """レースごとに、絞り方に合うか（真偽）。"""
        values = traits[self.trait]
        mask = pd.Series(True, index=traits.index)
        if self.low is not None:
            mask &= values >= self.low
        if self.high is not None:
            mask &= values <= self.high
        return mask


#: 2016〜2018年だけで立てた、券種ごとの仮説の絞り方（docs/03 の 2）。
HYPOTHESES: dict[TicketType, RaceFilter] = {
    TicketType.EXACTA: RaceFilter("field_size", None, 15, "15頭以下"),
    TicketType.WIDE: RaceFilter("favorite_odds", 2.9, None, "1番人気が 2.9倍以上"),
    TicketType.TRIO: RaceFilter("has_danger", None, 0, "危険な人気馬がいない"),
    TicketType.TRIFECTA: RaceFilter("top_value", None, 0.99, "◎ の単勝の期待値が 0.99 以下"),
    TicketType.QUINELLA: RaceFilter("favorite_odds", None, 1.9, "1番人気が 1.9倍以下"),
}
