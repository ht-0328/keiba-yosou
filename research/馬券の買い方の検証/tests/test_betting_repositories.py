"""契約: 4つのリポジトリは、期間の確定オッズ・払戻の明細・払戻のフラグ・レースの属性を、合成DB から決まった列で読む。

確定オッズは親のデータ区分 4・5 の断面だけを使い、締め切り前の断面と混ぜない。表が無い DB では空で返る。
"""

from datetime import date
from pathlib import Path

import duckdb
import pytest

from 合成DB import synth

from yosou.shared.betting import TicketType
from yosou.shared.repository import (
    REFUNDED,
    FinalOddsRepository,
    PayoutFlagRepository,
    PayoutRepository,
    RaceDayRange,
    void_column,
)

from 馬券の買い方の検証.analysis.repository import RaceFactRepository

_DAYS = RaceDayRange(date(2025, 7, 1), date(2025, 7, 31))
_RACE_1 = "2025070605010101"
_RACE_2 = "2025070605010102"


@pytest.fixture
def con(betting_db: Path):
    connection = duckdb.connect(str(betting_db), read_only=True)
    yield connection
    connection.close()


def test_day_range_rejects_reversed_days():
    with pytest.raises(ValueError):
        RaceDayRange(date(2025, 7, 31), date(2025, 7, 1))
    assert _DAYS.params == ["20250701", "20250731"]


def test_final_odds_use_the_final_snapshot_and_drop_no_vote_rows(con):
    odds = FinalOddsRepository(con, TicketType.WIN).read(_DAYS)
    assert list(odds.columns) == ["race_id", "combo", "odds", "popularity"]
    assert list(odds["combo"]) == ["01", "02", "03", "04"]
    assert list(odds["odds"]) == [2.0, 4.5, 8.0, 15.0]
    assert list(odds["race_id"].unique()) == [_RACE_1]


def test_final_odds_of_range_and_combination_types(con):
    place = FinalOddsRepository(con, TicketType.PLACE).read(_DAYS)
    assert list(place.columns) == ["race_id", "combo", "odds", "odds_high", "popularity"]
    assert list(place["odds"]) == [3.0] and list(place["odds_high"]) == [4.5]
    trio = FinalOddsRepository(con, TicketType.TRIO).read(_DAYS)
    assert list(trio["combo"]) == ["020304"] and list(trio["odds"]) == [178.5] and list(trio["popularity"]) == [14]
    trifecta = FinalOddsRepository(con, TicketType.TRIFECTA).read(_DAYS)
    assert list(trifecta["odds"]) == [12345.6]
    wide = FinalOddsRepository(con, TicketType.WIDE).read(_DAYS)
    assert list(wide["odds"]) == [50.3] and list(wide["odds_high"]) == [53.8]


def test_final_odds_outside_the_period_are_not_read(con):
    odds = FinalOddsRepository(con, TicketType.WIN).read(RaceDayRange(date(2025, 8, 1), date(2025, 8, 31)))
    assert odds.empty and list(odds.columns) == ["race_id", "combo", "odds", "popularity"]


def test_payouts_keep_every_row_in_sequence(con):
    wide = PayoutRepository(con, TicketType.WIDE).read(_DAYS)
    assert list(wide.columns) == ["race_id", "combo", "yen", "popularity", "seq"]
    assert list(wide["combo"]) == ["0204", "0304", "0203"] and list(wide["yen"]) == [900, 1500, 400]
    win = PayoutRepository(con, TicketType.WIN).read(_DAYS)
    assert list(win[win["race_id"] == _RACE_1]["combo"]) == ["04"] and list(win[win["race_id"] == _RACE_1]["yen"]) == [1500]
    place = PayoutRepository(con, TicketType.PLACE).read(_DAYS)
    assert len(place[place["race_id"] == _RACE_1]) == 3
    assert list(PayoutRepository(con, TicketType.EXACTA).read(_DAYS)["combo"]) == ["0402"]


def test_payout_flags_mark_void_ticket_types_and_refunds(con):
    flags = PayoutFlagRepository(con).read(_DAYS).set_index("race_id")
    assert void_column(TicketType.TRIFECTA) == "trifecta_void"
    assert bool(flags.loc[_RACE_1, "trifecta_void"]) is False and bool(flags.loc[_RACE_2, "trifecta_void"]) is True
    assert bool(flags.loc[_RACE_1, REFUNDED]) is True and bool(flags.loc[_RACE_2, REFUNDED]) is False
    assert bool(flags.loc[_RACE_2, void_column(TicketType.WIN)]) is False


def test_race_facts_have_one_row_per_race(con):
    races = RaceFactRepository(con).read(_DAYS)
    assert list(races["race_id"]) == [_RACE_1, _RACE_2]
    assert list(races["race_no"]) == [1, 2] and list(races["field_size"]) == [5, 5]
    assert list(races["venue_code"]) == ["05", "05"] and list(races["grade_code"]) == ["", ""]
    assert races["race_date"].iloc[0].strftime("%Y-%m-%d") == "2025-07-06"


def test_missing_tables_give_empty_frames(tmp_path: Path):
    path = synth.build_db(tmp_path / "bare.duckdb", tables={"ra": synth.simple_race().ra, "se": synth.simple_race().se})
    con = duckdb.connect(str(path), read_only=True)
    try:
        assert FinalOddsRepository(con, TicketType.TRIO).read(_DAYS).empty
        assert PayoutRepository(con, TicketType.WIDE).read(_DAYS).empty
        flags = PayoutFlagRepository(con).read(_DAYS)
        assert flags.empty and REFUNDED in flags.columns
    finally:
        con.close()
