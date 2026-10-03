"""締め切り前の券種オッズ（``AnnouncedTicketOddsRepository``）のテスト。値は架空。DB は合成DB だけを使う。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from 共通 import keys
from 合成DB import synth

from ..betting import TicketType
from ..repository import AnnouncedTicketOddsRepository


@pytest.fixture(scope="module")
def odds_db(tmp_path_factory) -> tuple[Path, str]:
    """1レースに、3連単の締め切り前の断面を2つ（古い 11:00 と新しい 12:00）と確定（データ区分 5）、複勝の締め切り前の断面を入れた合成DB。"""
    sample = synth.simple_race()
    ra = sample.ra[0]
    for stage, announced, tenths in (("1", "04061100", 10000), ("1", "04061200", 12345), ("5", "00000000", 20000)):
        sample.odds.append(("o6", synth.odds_header(ra, "o6", stage=stage, announced=announced)))
        sample.odds.append(("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "040203", tenths, announced=announced)))
        sample.odds.append(("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "010203", 0, seq=2, announced=announced)))  # 無投票
    sample.odds.append(("o1", synth.odds_header(ra, "o1", stage="2", announced="04061200")))
    sample.odds.append(("o1__複勝オッズ", synth.range_odds_row(ra, "o1__複勝オッズ", "03", 18, 24, announced="04061200")))
    path = synth.build_db(tmp_path_factory.mktemp("odds") / "announced.duckdb", sample)
    return path, "".join(ra[column] for column in keys.RACE_KEY)


def test_reads_the_latest_snapshot_before_final_and_drops_no_vote(odds_db) -> None:
    path, race_id = odds_db
    con = duckdb.connect(str(path), read_only=True)
    board = AnnouncedTicketOddsRepository(con, TicketType.TRIFECTA).read(race_id).set_index("combo")
    assert list(board.index) == ["040203"] and board.loc["040203", "odds"] == pytest.approx(1234.5)  # 12:00 の断面（確定の 2000.0 ではない）


def test_place_odds_are_the_low_end_of_the_range(odds_db) -> None:
    path, race_id = odds_db
    con = duckdb.connect(str(path), read_only=True)
    board = AnnouncedTicketOddsRepository(con, TicketType.PLACE).read(race_id).set_index("combo")
    assert board.loc["03", "odds"] == pytest.approx(1.8)


def test_empty_when_there_is_no_snapshot(odds_db) -> None:
    path, race_id = odds_db
    con = duckdb.connect(str(path), read_only=True)
    assert AnnouncedTicketOddsRepository(con, TicketType.TRIO).read(race_id).empty
    assert AnnouncedTicketOddsRepository(con, TicketType.TRIFECTA).read("2024040601010199").empty
