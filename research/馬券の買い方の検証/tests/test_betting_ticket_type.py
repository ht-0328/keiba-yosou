"""契約: 券種は7つで、それぞれ払戻・オッズの表、馬の数、着順の区別、対応する荒れ具合の券種を持つ。"""

import pytest

from yosou.upset_level.dataset import BetType

from 馬券の買い方の検証.analysis.ticket import TicketType


def test_specs_follow_the_bet_rules():
    assert TicketType.TRIFECTA.spec.is_ordered and not TicketType.TRIO.spec.is_ordered
    assert TicketType.WIDE.spec.has_odds_range and TicketType.PLACE.spec.has_odds_range
    assert TicketType.WIN.spec.horse_count == 1 and TicketType.TRIO.spec.horse_count == 3
    assert TicketType.WIDE.spec.upset_bet is BetType.QUINELLA and TicketType.PLACE.spec.upset_bet is BetType.WIN
    assert TicketType.EXACTA.spec.payout_table == "hr__馬単払戻" and TicketType.EXACTA.spec.combo_column == "組番"
    assert not TicketType.WIN.is_combination and TicketType.QUINELLA.is_combination


def test_parse_reads_the_label():
    assert TicketType.parse(" 3連複 ") is TicketType.TRIO
    with pytest.raises(ValueError):
        TicketType.parse("枠連")
