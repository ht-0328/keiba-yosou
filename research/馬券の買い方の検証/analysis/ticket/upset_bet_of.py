"""券種と、荒れ具合の予想の券種の対応。"""

from __future__ import annotations

from yosou.shared.betting import TicketType
from yosou.upset_level.dataset import BetType

#: 券種 → 荒れ具合の予想で対応させる券種（複勝は単勝、ワイド・馬単は馬連の荒れ具合で見る）。
#: 共通の ``TicketType`` は予想のパッケージを参照しないので、この対応は研究の中に置く。
_UPSET_BETS: dict[TicketType, BetType] = {
    TicketType.WIN: BetType.WIN,
    TicketType.PLACE: BetType.WIN,
    TicketType.QUINELLA: BetType.QUINELLA,
    TicketType.EXACTA: BetType.QUINELLA,
    TicketType.WIDE: BetType.QUINELLA,
    TicketType.TRIO: BetType.TRIO,
    TicketType.TRIFECTA: BetType.TRIFECTA,
}


def upset_bet_of(ticket_type: TicketType) -> BetType:
    """その券種の買い方で、どの券種の荒れ具合を見るか。"""
    return _UPSET_BETS[ticket_type]
