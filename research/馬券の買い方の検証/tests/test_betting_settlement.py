"""契約: 精算は、買い目を組番で払戻と照合し（複勝・ワイドの複数行も同着も全部足す）、不成立やオッズ無しは理由つきで見送る。"""

import pandas as pd

from 馬券の買い方の検証.analysis import column_names as names
from 馬券の買い方の検証.analysis.race_material import RaceMaterials
from 馬券の買い方の検証.analysis.repository import REFUNDED, void_column
from 馬券の買い方の検証.analysis.settlement import (
    SKIP_NO_ODDS,
    SKIP_NO_PAYOUT,
    SKIP_NOTHING_LEFT,
    SKIP_VOID,
    OddsBook,
    OddsFloorCut,
    PayoutBook,
    PlanResult,
    PlanSettler,
    SettlementTable,
)
from 馬券の買い方の検証.analysis.ticket import Ticket, TicketType, plan_named

from betting_fixtures import RACE_ID, runners

_RACE_2 = "2025070605010102"


def _payouts(race_id=RACE_ID):
    def table(rows):
        return pd.DataFrame(rows, columns=["race_id", "combo", "yen", "popularity", "seq"])
    return {
        TicketType.WIN: table([(race_id, "06", 900, 6, 1)]),
        TicketType.PLACE: table([(race_id, "06", 300, 6, 1), (race_id, "02", 300, 2, 2), (race_id, "03", 300, 3, 3)]),
        TicketType.WIDE: table([(race_id, "0206", 800, 9, 1), (race_id, "0306", 1200, 12, 2), (race_id, "0203", 400, 2, 3)]),
        TicketType.TRIO: table([(race_id, "020306", 5000, 20, 1)]),
        TicketType.TRIFECTA: table([(race_id, "060203", 30000, 90, 1), (race_id, "060203", 30000, 90, 2)]),
    }


def _flags(void_trifecta=False):
    row = {"race_id": RACE_ID, REFUNDED: False, **{void_column(t): False for t in TicketType}}
    row[void_column(TicketType.TRIFECTA)] = void_trifecta
    return pd.DataFrame([row])


def test_payout_book_sums_all_matching_rows():
    book = PayoutBook(_payouts(), _flags())
    assert book.payout_yen(RACE_ID, Ticket(TicketType.WIN, (6,))) == 900
    assert book.payout_yen(RACE_ID, Ticket(TicketType.WIN, (1,))) == 0
    assert book.payout_yen(RACE_ID, Ticket(TicketType.WIDE, (6, 2))) == 800
    assert book.payout_yen(RACE_ID, Ticket(TicketType.TRIO, (6, 3, 2))) == 5000
    assert book.payout_yen(RACE_ID, Ticket(TicketType.TRIFECTA, (6, 2, 3))) == 60000  # 同着の2行を足す
    assert book.payout_yen(RACE_ID, Ticket(TicketType.TRIFECTA, (2, 6, 3))) == 0
    assert book.has_race(RACE_ID) and not book.has_race(_RACE_2) and book.race_count == 1
    assert not book.is_void(RACE_ID, TicketType.TRIFECTA)
    assert PayoutBook(_payouts(), _flags(void_trifecta=True)).is_void(RACE_ID, TicketType.TRIFECTA)


def test_odds_cut_drops_low_odds_and_reports_missing_odds():
    odds = OddsBook({TicketType.TRIO: pd.DataFrame(
        [(RACE_ID, "020306", 50.0, 20), (RACE_ID, "010203", 12.0, 1), (RACE_ID, "010206", 150.0, 30)],
        columns=["race_id", "combo", "odds", "popularity"],
    )})
    cut = OddsFloorCut(odds)
    tickets = [Ticket(TicketType.TRIO, (1, 2, 3)), Ticket(TicketType.TRIO, (1, 2, 6)), Ticket(TicketType.TRIO, (2, 3, 6)), Ticket(TicketType.TRIO, (7, 8, 9))]
    kept = cut.apply(RACE_ID, tickets, 100.0)
    assert [ticket.combo for ticket in kept] == ["010206", "070809"]  # オッズの無い組は残す
    assert cut.apply(_RACE_2, tickets, 100.0) is None
    assert cut.apply(RACE_ID, [], 100.0) == []


def _materials(rows):
    races = pd.DataFrame({names.RACE_ID: [RACE_ID], names.RACE_DATE: [pd.Timestamp("2025-07-06")]})
    return RaceMaterials(races, rows)


def test_settler_settles_each_race_with_skip_reasons():
    rows = runners(top_odds=2.5)
    book = PayoutBook(_payouts(), _flags())
    cut = OddsFloorCut(OddsBook({}))
    results = PlanSettler(plan_named("本命→穴馬3 ワイド"), _materials(rows), book, cut).settle_all()
    assert results == [PlanResult(RACE_ID, "本命→穴馬3 ワイド", 3, 300, 0, 0)]  # 本命1番からの流しは外れ
    place = PlanSettler(plan_named("1番人気 複勝"), _materials(rows), book, cut).settle_all()[0]
    assert place.payout_yen == 0 and place.points == 1
    win = PlanSettler(plan_named("本命単勝"), _materials(rows), book, cut).settle_all()[0]
    assert win.points == 1 and win.payout_yen == 0
    rows_6_top = rows.copy()
    rows_6_top.loc[rows_6_top[names.HORSE_NO] == 6, names.FORM_PROB] = 0.99
    hit = PlanSettler(plan_named("本命複勝"), _materials(rows_6_top), book, cut).settle_all()[0]
    assert hit.payout_yen == 300 and hit.hit_count == 1 and hit.is_bet


def test_settler_skips_void_missing_payout_and_missing_odds():
    rows = runners()
    void_book = PayoutBook(_payouts(), _flags(void_trifecta=True))
    cut = OddsFloorCut(OddsBook({}))
    assert PlanSettler(plan_named("3連単 待ちの型"), _materials(rows), void_book, cut).settle_all()[0].skipped == SKIP_VOID
    other = rows.assign(**{names.RACE_ID: _RACE_2})
    materials = RaceMaterials(pd.DataFrame({names.RACE_ID: [_RACE_2], names.RACE_DATE: [pd.Timestamp("2025-07-06")]}), other)
    assert PlanSettler(plan_named("本命複勝"), materials, void_book, cut).settle_all()[0].skipped == SKIP_NO_PAYOUT
    book = PayoutBook(_payouts(), _flags())
    assert PlanSettler(plan_named("3連複 1-2-10（100倍未満カット）"), _materials(rows), book, cut).settle_all()[0].skipped == SKIP_NO_ODDS
    low_odds = OddsBook({TicketType.TRIO: pd.DataFrame(
        [(RACE_ID, f"{a:02d}{b:02d}{c:02d}", 5.0, 1) for a in (1,) for b in range(2, 17) for c in range(2, 17) if b < c],
        columns=["race_id", "combo", "odds", "popularity"],
    )})
    result = PlanSettler(plan_named("3連複 1-2-10（100倍未満カット）"), _materials(rows), book, OddsFloorCut(low_odds)).settle_all()[0]
    assert result.skipped == SKIP_NOTHING_LEFT


def test_settlement_table_round_trip(tmp_path):
    results = [PlanResult(RACE_ID, "本命複勝", 1, 100, 300, 1), PlanResult.skip(_RACE_2, "本命複勝", SKIP_VOID)]
    table = SettlementTable.from_results(results)
    table.write(tmp_path / "settlement.csv")
    loaded = SettlementTable.read(tmp_path / "settlement.csv")
    assert loaded.plan_names == ["本命複勝"]
    rows = loaded.for_plan("本命複勝")
    assert rows.loc[RACE_ID, "payout_yen"] == 300 and pd.isna(rows.loc[RACE_ID, "skipped"])
    assert rows.loc[_RACE_2, "skipped"] == SKIP_VOID and rows.loc[_RACE_2, "points"] == 0
