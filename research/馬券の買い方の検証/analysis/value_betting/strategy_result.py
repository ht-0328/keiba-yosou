"""戦略を、いくつかの区切りで評価した結果。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .strategy import Round3Strategy
from .ticket_summary import TicketSummary


@dataclass(frozen=True)
class StrategyResult:
    """1つの戦略を、段階の区切り（探索なら4つ）のテスト期間で評価した結果。

    - ``by_window``: 区切りの名前 → その区切りのまとめ。``lines``: 区切りの名前 → 使った線（決まらなければ NaN）。
    - ``total``: 区切りを合わせたまとめ（採否はこれで決める）。
    - ``tickets``: 買った買い目（全区切り）。
    """

    strategy: Round3Strategy
    by_window: dict[str, TicketSummary]
    lines: dict[str, float]
    total: TicketSummary
    tickets: pd.DataFrame

    @property
    def rate(self) -> float:
        return self.total.rate

    def windows_at_or_above(self, rate: float) -> int:
        """回収率が ``rate`` 以上の区切りの数（買っていない区切りは数えない）。"""
        return sum(1 for summary in self.by_window.values() if not np.isnan(summary.rate) and summary.rate >= rate)
