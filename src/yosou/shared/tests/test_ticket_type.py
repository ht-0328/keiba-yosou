"""契約: 券種は7つで、それぞれ払戻・オッズの表、馬の数、着順の区別を持つ。書き方と英語の短い名前から引ける。"""

import pytest

from yosou.shared.betting import TicketType


def test_specs_follow_the_bet_rules():
    assert TicketType.TRIFECTA.spec.is_ordered and not TicketType.TRIO.spec.is_ordered
    assert TicketType.WIDE.spec.has_odds_range and TicketType.PLACE.spec.has_odds_range
    assert TicketType.WIN.spec.horse_count == 1 and TicketType.TRIO.spec.horse_count == 3
    assert TicketType.EXACTA.spec.payout_table == "hr__馬単払戻" and TicketType.EXACTA.spec.combo_column == "組番"
    assert not TicketType.WIN.is_combination and TicketType.QUINELLA.is_combination
    # 払戻率は JRA の券種ごとの決まり（単勝・複勝 80%、馬連・ワイド 77.5%、馬単・3連複 75%、3連単 72.5%）
    assert TicketType.WIN.spec.payout_rate == 0.8 and TicketType.TRIO.spec.payout_rate == 0.75 and TicketType.TRIFECTA.spec.payout_rate == 0.725


def test_parse_reads_the_label():
    assert TicketType.parse(" 3連複 ") is TicketType.TRIO
    with pytest.raises(ValueError):
        TicketType.parse("枠連")


def test_of_key_reads_the_english_name():
    assert TicketType.of_key("wide") is TicketType.WIDE
    with pytest.raises(ValueError):
        TicketType.of_key("bracket")
