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

#: 架空の16頭のレースで、型どおりに作ったときの点数（None は「候補が足りない」で見送り）。
EXPECTED_POINTS = {
    "本命単勝": 1, "本命複勝": 1, "本命→穴馬3 ワイド": 3, "本命→穴馬3 馬連": 3, "3連複 1-2-4": 5, "3連単 1-2-5": 8,
    "3連単 人気の和": 6, "穴馬軸→1〜3番人気 ワイド": 6, "本命→穴馬5 馬連": 5, "3連複 1-2-10": 17, "3連複 1-3-10": 24,
    "3連単 待ちの型": 24, "3連複 1-2-10（100倍未満カット）": 17, "3連複 1-3-10（100倍未満カット）": 24,
    "3連単 待ちの型（200倍未満カット）": 24, "1番人気 単勝": 1, "1番人気 複勝": 1,
    # 値で絞る買い方（穴馬の確率: 6番 0.32・7番 0.29・8番 0.26・9番 0.23・10番 0.20・11番 0.17 …。単勝 10〜19.9倍は 7〜13番）
    "穴馬 確率≥0.25 複勝": 3, "穴馬 確率≥0.30 複勝": 1, "穴馬 確率≥0.35 複勝": None, "穴馬 確率≥0.40 複勝": None,
    "穴馬 確率≥0.25 単勝（10〜19.9倍）": 2, "穴馬 確率≥0.30 単勝（10〜19.9倍）": None, "穴馬 確率≥0.35 単勝（10〜19.9倍）": None,
    # 期待値 = 確率 × 複勝オッズ（1 + 0.5 × 人気）。本命は 0.85 × 1.5 = 1.275、全頭は 16番だけ 0.9、穴馬は 6〜11番が 1.1 以上・6〜10番が 1.2 以上
    "本命 複勝 期待値≥1.0": 1, "本命 複勝 期待値≥1.1": 1, "本命 複勝 期待値≥1.2": 1,
    "全頭 複勝 期待値≥1.0": 15, "全頭 複勝 期待値≥1.1": 15, "全頭 複勝 期待値≥1.2": 15,
    "穴馬 複勝 期待値≥1.0": 6, "穴馬 複勝 期待値≥1.1": 6, "穴馬 複勝 期待値≥1.2": 5,
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
    if EXPECTED_POINTS[name] is None:
        assert built.skipped == SKIP_NO_CANDIDATES
        return
    assert built.skipped is None, built.skipped
    assert built.points == EXPECTED_POINTS[name]


def test_value_pickers_follow_thresholds_and_odds_band():
    rows = runners()
    assert sorted(ticket.horses[0] for ticket in TicketBuilder(plan_named("穴馬 確率≥0.25 複勝")).build(rows).tickets) == [6, 7, 8]
    assert sorted(ticket.horses[0] for ticket in TicketBuilder(plan_named("穴馬 確率≥0.25 単勝（10〜19.9倍）")).build(rows).tickets) == [7, 8]
    assert [ticket.horses[0] for ticket in TicketBuilder(plan_named("本命 複勝 期待値≥1.2")).build(rows).tickets] == [1]
    assert sorted(ticket.horses[0] for ticket in TicketBuilder(plan_named("穴馬 複勝 期待値≥1.2")).build(rows).tickets) == [6, 7, 8, 9, 10]
    no_odds = rows.assign(place_odds=float("nan"))
    assert TicketBuilder(plan_named("全頭 複勝 期待値≥1.0")).build(no_odds).skipped == SKIP_NO_CANDIDATES


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
