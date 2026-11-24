"""5つの券種の既定の帯と、期待値の線の既定。"""

from __future__ import annotations

from yosou.shared.betting import TicketType

from .payout_band import PayoutBand

#: 券種ごとの既定の帯（学ぶ下限・高配当の線・上限）。
DEFAULT_BANDS: dict[TicketType, PayoutBand] = {
    TicketType.WIDE: PayoutBand(TicketType.WIDE, learn_from=3.0, high_line=10.0, cap=300.0),
    TicketType.QUINELLA: PayoutBand(TicketType.QUINELLA, learn_from=8.0, high_line=30.0, cap=1_000.0),
    TicketType.EXACTA: PayoutBand(TicketType.EXACTA, learn_from=15.0, high_line=60.0, cap=3_000.0),
    TicketType.TRIO: PayoutBand(TicketType.TRIO, learn_from=20.0, high_line=100.0, cap=3_000.0),
    TicketType.TRIFECTA: PayoutBand(TicketType.TRIFECTA, learn_from=100.0, high_line=500.0, cap=10_000.0),
}
#: 期待値の線の既定。期待値（確率 × オッズ）がこの値以上の組を買う。
DEFAULT_VALUE_LINE = 1.05
