"""鍵・条件・最新行の選び方の契約。"""

from __future__ import annotations

import duckdb
import pytest

from 共通 import keys


def test_q_wraps_and_escapes_double_quotes():
    assert keys.q("開催回[第N回]") == '"開催回[第N回]"'
    assert keys.q('a"b') == '"a""b"'
    assert keys.col("距離", "r") == 'r."距離"'


def test_rid_expr_joins_all_six_key_columns():
    expr = keys.rid_expr("s")
    assert expr.count("||") == 5
    for name in keys.RACE_KEY:
        assert keys.col(name, "s") in expr


def test_split_rid_and_condition():
    values = keys.split_rid("2026090605040211")
    assert values == {
        "開催年": "2026", "開催月日": "0906", "競馬場コード": "05",
        "開催回[第N回]": "04", "開催日目[N日目]": "02", "レース番号": "11",
    }
    clause, params = keys.rid_condition("2026090605040211", "ra")
    assert clause.count("= ?") == 6 and params == ["2026", "0906", "05", "04", "02", "11"]


@pytest.mark.parametrize("bad", ["", "2026", "20260906050402111", "2026090605040A11"])
def test_split_rid_rejects_wrong_length_or_letters(bad):
    with pytest.raises(ValueError):
        keys.split_rid(bad)


def test_validate_hid():
    assert keys.validate_hid(" 2021100001 ") == "2021100001"
    with pytest.raises(ValueError):
        keys.validate_hid("21100001")


def test_latest_qualify_keeps_final_row_over_entry_row():
    con = duckdb.connect()
    con.execute('CREATE TABLE t ("開催年" VARCHAR, "レース番号" VARCHAR, "データ区分" VARCHAR, "データ作成年月日" VARCHAR, v VARCHAR)')
    con.execute("INSERT INTO t VALUES ('2024','01','2','20240405','entry'), ('2024','01','7','20240408','final'), ('2024','01','5','20240406','flash')")
    rows = con.execute(f"SELECT v FROM t {keys.latest_qualify(('開催年', 'レース番号'))}").fetchall()
    assert rows == [("final",)]


def test_jra_only_drops_local_and_overseas_codes():
    con = duckdb.connect()
    con.execute('CREATE TABLE t ("競馬場コード" VARCHAR)')
    con.execute("INSERT INTO t VALUES ('01'), ('10'), ('30'), ('A4'), ('05')")
    rows = con.execute(f"SELECT \"競馬場コード\" FROM t WHERE {keys.jra_only()} ORDER BY 1").fetchall()
    assert [r[0] for r in rows] == ["01", "05", "10"]


def test_race_date_expr_builds_iso_date():
    con = duckdb.connect()
    con.execute('CREATE TABLE t ("開催年" VARCHAR, "開催月日" VARCHAR)')
    con.execute("INSERT INTO t VALUES ('2024','0406')")
    assert con.execute(f"SELECT {keys.race_date_expr()} FROM t").fetchone()[0] == "2024-04-06"


def test_final_only_uses_final_stages():
    assert keys.final_only("se") == 'se."データ区分" IN (\'5\', \'6\', \'7\')'
