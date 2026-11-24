"""ある期間の、確定オッズの板と払戻。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.betting import TicketType


@dataclass(frozen=True)
class FinalMarket:
    """ある期間（1か月など）のレースの、確定の市場の結果。``FinalMarketLoader.load`` が作る。

    - ``boards``: 券種 → 確定オッズの板（列 ``race_id``・``combo``・``odds``。ワイドは最低オッズ）。5券種ぶん。
    - ``payouts``: 券種 → 払戻の明細（``PayoutRepository.read`` の形。列 ``race_id``・``combo``・``yen`` ほか）。表を作る券種ぶん。
    """

    boards: dict[TicketType, pd.DataFrame]
    payouts: dict[TicketType, pd.DataFrame]
