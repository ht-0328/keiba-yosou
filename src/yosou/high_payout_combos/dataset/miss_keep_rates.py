"""学習の行に残す、外れの組の割合。"""

from __future__ import annotations

from yosou.shared.betting import TicketType

#: 券種ごとの、外れの組を学習に残す割合。組の多い券種ほど小さくして、学習の行の数を券種の間でそろえる。
MISS_KEEP_RATES: dict[TicketType, float] = {
    TicketType.WIDE: 0.3,
    TicketType.QUINELLA: 0.2,
    TicketType.EXACTA: 0.1,
    TicketType.TRIO: 0.06,
    TicketType.TRIFECTA: 0.015,
}
#: 間引きの乱数の種は「この値 ＋ 年」。年ごとに固定して、何度作っても同じ行が残るようにする。
SEED_BASE = 1000
