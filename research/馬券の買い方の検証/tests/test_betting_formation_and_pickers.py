"""契約: フォーメーションは列の直積から同じ馬の組を除き、順不同は1つにする。選び方は決まった順で馬番を返し、使った馬を避ける。"""

import pytest

from yosou.shared.betting import TicketType

from 馬券の買い方の検証.analysis.ticket import FormationTickets, Ticket
from 馬券の買い方の検証.analysis.ticket.picker import (
    CombinedPicker,
    FormRankPicker,
    LongshotRankPicker,
    MidPopularityByLongshotPicker,
    PopularityPicker,
)

from betting_fixtures import runners


def test_ticket_normalizes_unordered_and_keeps_ordered():
    assert Ticket(TicketType.TRIO, (4, 2, 3)).combo == "020304"
    assert Ticket(TicketType.TRIFECTA, (4, 2, 3)).combo == "040203"
    assert Ticket(TicketType.QUINELLA, (4, 2)) == Ticket(TicketType.QUINELLA, (2, 4))
    with pytest.raises(ValueError):
        Ticket(TicketType.QUINELLA, (2, 2))
    with pytest.raises(ValueError):
        Ticket(TicketType.WIN, (1, 2))


def test_formation_counts_match_the_rule_book():
    formation = FormationTickets()
    assert len(formation.build(TicketType.TRIO, [[1], [2, 3], [2, 3, 6, 7]])) == 5          # 1-2-4
    assert len(formation.build(TicketType.TRIO, [[1], [6, 7], [6, 7, 8, 9, 10, 11, 12, 13, 14, 15]])) == 17  # 1-2-10
    assert len(formation.build(TicketType.TRIFECTA, [[6, 7, 8, 9], [1, 2], [6, 7, 8, 9]])) == 24   # 待ちの型
    assert len(formation.build(TicketType.WIDE, [[6, 7], [1, 2, 3]])) == 6
    assert len(formation.box(TicketType.QUINELLA, [1, 2, 3, 4])) == 6
    assert len(formation.box(TicketType.TRIFECTA, [1, 2, 3])) == 6
    with pytest.raises(ValueError):
        formation.build(TicketType.QUINELLA, [[1]])


def test_form_rank_picker_skips_and_avoids_taken():
    rows = runners()
    assert FormRankPicker().pick(rows, 2, ()) == [1, 2]
    assert FormRankPicker(skip=1).pick(rows, 2, {1}) == [2, 3]
    assert FormRankPicker().pick(rows, 3, {1, 2}) == [3, 4, 5]
    assert FormRankPicker().pick(rows, 0, ()) == []


def test_longshot_picker_uses_only_longshots_and_zones():
    rows = runners()
    assert LongshotRankPicker().pick(rows, 3, ()) == [6, 7, 8]
    assert LongshotRankPicker(zone="大穴").pick(rows, 2, ()) == [10, 11]
    assert LongshotRankPicker().pick(rows, 2, {6}) == [7, 8]


def test_popularity_pickers():
    rows = runners()
    assert PopularityPicker(1, 3).pick(rows, 3, ()) == [1, 2, 3]
    assert PopularityPicker(3, 6).pick(rows, 4, {5, 6}) == [3, 4]
    assert MidPopularityByLongshotPicker(3, 9).pick(rows, 4, ()) == [6, 7, 8, 9]
    assert CombinedPicker(((FormRankPicker(skip=1), 1), (LongshotRankPicker(), 2))).pick(rows, 3, {1}) == [2, 6, 7]
    with pytest.raises(ValueError):
        PopularityPicker(3, 2)
