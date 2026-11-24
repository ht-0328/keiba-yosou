"""1つの券種の、オッズの帯。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.betting import TicketType


@dataclass(frozen=True)
class PayoutBand:
    """1つの券種の「学ぶ下限・高配当の線・上限」（オッズの倍率。ワイドは最低オッズ）。

    - ``learn_from``: 学ぶ下限。この倍率以上の組を学習と予測の対象にする。
    - ``high_line``: 高配当の線。買うのはこの倍率以上の組だけ（学ぶ行は、線より下まで広げてある）。
    - ``cap``: 上限。この倍率以上の組は学ばず、買わない。
    例: 馬連は 8倍から学び、30倍以上・1,000倍未満を買う。
    """

    ticket_type: TicketType
    learn_from: float
    high_line: float
    cap: float

    def __post_init__(self) -> None:
        if not 0 < self.learn_from <= self.high_line < self.cap:
            raise ValueError(
                f"帯は 0 < 学ぶ下限 ≦ 高配当の線 < 上限 にしてください: {self.ticket_type.label} {self.learn_from}・{self.high_line}・{self.cap}"
            )

    def is_learnable(self, odds: pd.Series) -> pd.Series:
        """学習と予測の対象のオッズか（学ぶ下限以上・上限未満）。"""
        return (odds >= self.learn_from) & (odds < self.cap)

    def is_high_payout(self, odds: pd.Series) -> pd.Series:
        """買う対象のオッズか（高配当の線以上・上限未満）。"""
        return (odds >= self.high_line) & (odds < self.cap)
