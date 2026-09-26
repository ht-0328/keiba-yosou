"""契約: 券種ごとに、見る荒れ具合の券種が決まっている（複勝は単勝、ワイド・馬単は馬連）。

券種そのもの（表の名前・馬の数・着順の区別）の契約は、共通の ``src/yosou/shared/tests/test_ticket_type.py``。
"""

from yosou.shared.betting import TicketType
from yosou.upset_level.dataset import BetType

from 馬券の買い方の検証.analysis.ticket import upset_bet_of


def test_every_ticket_type_has_an_upset_bet():
    assert {ticket_type: upset_bet_of(ticket_type) for ticket_type in TicketType} == {
        TicketType.WIN: BetType.WIN, TicketType.PLACE: BetType.WIN,
        TicketType.QUINELLA: BetType.QUINELLA, TicketType.EXACTA: BetType.QUINELLA, TicketType.WIDE: BetType.QUINELLA,
        TicketType.TRIO: BetType.TRIO, TicketType.TRIFECTA: BetType.TRIFECTA,
    }
