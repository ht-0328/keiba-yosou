"""第3段: 買い目を、確定着順と確定オッズで精算する。"""

from __future__ import annotations

from collections.abc import Mapping, Set

import pandas as pd

from yosou.shared.dataset import RACE_ID

from .ticket_maker import COMBO, ODDS, STAKE

#: 足す列の名前。
HIT, PAYOUT = "的中", "払戻"


class TicketSettler:
    """買い目の表に、的中したか（``winners`` の組に入っているか）と払戻（確定オッズ × 掛け金）を足す。

    ``winners`` はレースID → 当たりの組の集まり。3連単なら着順の並び、3連複なら馬番の小さい順で渡す。
    払戻は 100円あたりの確定オッズから計算する（同着のレースでは、実際の払戻とわずかにずれることがある）。
    """

    def settle(self, tickets: pd.DataFrame, winners: Mapping[str, Set[tuple[int, ...]]]) -> pd.DataFrame:
        hit = [combo in winners.get(race_id, frozenset()) for race_id, combo in zip(tickets[RACE_ID], tickets[COMBO])]
        settled = tickets.assign(**{HIT: hit})
        return settled.assign(**{PAYOUT: (settled[ODDS] * settled[STAKE]).where(settled[HIT], 0.0)})
