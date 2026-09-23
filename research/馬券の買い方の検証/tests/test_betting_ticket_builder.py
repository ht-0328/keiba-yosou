"""契約: 買い方の目録のそれぞれが、架空の16頭のレースで型どおりの点数の買い目を作り、買う条件に合わないレースは理由つきで見送る。"""

import pytest

from 馬券の買い方の検証.analysis.ticket import (
    SKIP_LOW_ODDS,
    SKIP_NO_CANDIDATES,
    SKIP_TOP_NOT_FAVORITE,
    ALL_PLANS,
    BASELINE_PLANS,
    NARROW_PLANS,
    WIDE_PLANS,
    Breadth,
    DangerousFavoriteFilter,
    TicketBuilder,
    TicketType,
    plan_named,
)

from betting_fixtures import runners

#: 架空の16頭のレースで、型どおりに作ったときの点数。
EXPECTED_POINTS = {
    "本命単勝": 1, "本命複勝": 1, "本命→穴馬3 ワイド": 3, "本命→穴馬3 馬連": 3, "3連複 1-2-4": 5, "3連単 1-2-5": 8,
    "3連単 人気の和": 6, "穴馬軸→1〜3番人気 ワイド": 6, "本命→穴馬5 馬連": 5, "3連複 1-2-10": 17, "3連複 1-3-10": 24,
    "3連単 待ちの型": 24, "3連複 1-2-10（100倍未満カット）": 17, "3連複 1-3-10（100倍未満カット）": 24,
    "3連単 待ちの型（200倍未満カット）": 24, "1番人気 単勝": 1, "1番人気 複勝": 1,
}


def test_catalog_is_consistent():
    assert {plan.name for plan in ALL_PLANS} == set(EXPECTED_POINTS)
    assert all(plan.breadth is Breadth.NARROW for plan in NARROW_PLANS)
    assert all(plan.breadth is Breadth.WIDE for plan in WIDE_PLANS)
    assert all(plan.breadth is Breadth.NARROW for plan in BASELINE_PLANS)
    with pytest.raises(LookupError):
        plan_named("無い買い方")


@pytest.mark.parametrize("name", sorted(EXPECTED_POINTS))
def test_each_plan_makes_the_expected_points(name):
    built = TicketBuilder(plan_named(name)).build(runners(top_odds=2.5))
    assert built.skipped is None, built.skipped
    assert built.points == EXPECTED_POINTS[name]


def test_specific_tickets_follow_the_columns():
    trio = TicketBuilder(plan_named("3連複 1-2-4")).build(runners())
    assert sorted(ticket.combo for ticket in trio.tickets) == ["010203", "010206", "010207", "010306", "010307"]
    waiting = TicketBuilder(plan_named("3連単 待ちの型")).build(runners())
    assert all(ticket.horses[0] in (6, 7, 8, 9) and ticket.horses[1] in (1, 2) for ticket in waiting.tickets)
    popularity_sum = TicketBuilder(plan_named("3連単 人気の和")).build(runners())
    assert sorted(ticket.combo for ticket in popularity_sum.tickets) == ["010503", "010504", "010506", "010603", "010604", "010605"]


def test_dangerous_favorites_are_excluded_when_the_plan_says_so():
    rows = runners(top_danger=0.7)
    wide = TicketBuilder(plan_named("本命→穴馬3 ワイド")).build(rows)
    assert all(ticket.horses[0] == 2 for ticket in wide.tickets)
    quinella = TicketBuilder(plan_named("本命→穴馬3 馬連")).build(rows)
    assert all(ticket.horses[0] == 1 for ticket in quinella.tickets)
    assert DangerousFavoriteFilter(0.6).apply(rows)[ "horse_no"].tolist() == [2, 3] + list(range(6, 17))


def test_skips_have_reasons():
    assert TicketBuilder(plan_named("本命単勝")).build(runners(top_odds=1.5)).skipped == SKIP_LOW_ODDS
    rows = runners()
    rows.loc[rows["horse_no"] == 1, "popularity"], rows.loc[rows["horse_no"] == 2, "popularity"] = 2, 1
    assert TicketBuilder(plan_named("3連単 人気の和")).build(rows).skipped == SKIP_TOP_NOT_FAVORITE
    few = runners().head(5)
    assert TicketBuilder(plan_named("3連複 1-2-10")).build(few).skipped == SKIP_NO_CANDIDATES
    empty = runners().head(0)
    assert TicketBuilder(plan_named("本命複勝")).build(empty).skipped == SKIP_NO_CANDIDATES
    assert plan_named("3連単 1-2-5").ticket_type is TicketType.TRIFECTA
