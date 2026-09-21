"""コード表と逆引きの契約。"""

from __future__ import annotations

import duckdb
import pytest

from 共通 import codes


def test_venue_code_accepts_name_and_code():
    assert codes.venue_code("東京") == "05"
    assert codes.venue_code(" 05 ") == "05"
    assert codes.venue_name("06") == "中山"
    with pytest.raises(ValueError):
        codes.venue_code("大井")


def test_track_codes_accepts_name_and_code():
    assert codes.track_codes("芝・左") == ("11",)
    assert codes.track_codes("18") == ("18",)
    with pytest.raises(ValueError):
        codes.track_codes("芝・斜め")


@pytest.mark.parametrize("code,surface", [("10", "芝"), ("22", "芝"), ("23", "ダート"), ("29", "ダート"), ("51", "障害"), ("59", "障害"), ("", None), ("99", None)])
def test_surface_of(code, surface):
    assert codes.surface_of(code) == surface


def test_condition_and_surface_aliases():
    assert codes.condition_code("稍") == "2"
    assert codes.condition_code("良") == "1"
    assert codes.condition_code("4") == "4"
    assert codes.surface_name("ダ") == "ダート"
    assert codes.sex_name("セ") == "セン"
    with pytest.raises(ValueError):
        codes.condition_code("泥")


def test_class_name_prefers_grade_over_condition():
    assert codes.class_name("999", "A") == "G1"
    assert codes.class_name("999", "E") == "オープン"
    assert codes.class_name("005", " ") == "1勝クラス"
    assert codes.class_name("", "") == codes.UNKNOWN_CLASS


def test_sql_versions_agree_with_python_versions():
    con = duckdb.connect()
    con.execute("CREATE TABLE t (cond VARCHAR, grade VARCHAR, track VARCHAR)")
    cases = [("999", "A", "11"), ("999", "E", "24"), ("005", " ", "54"), ("", "", "99"), ("703", "L", "17")]
    con.executemany("INSERT INTO t VALUES (?, ?, ?)", cases)
    rows = con.execute(f"SELECT {codes.class_name_sql('cond', 'grade')}, {codes.surface_sql('track')} FROM t").fetchall()
    assert [r[0] for r in rows] == [codes.class_name(c, g) for c, g, _ in cases]
    assert [r[1] for r in rows] == [codes.surface_of(t) or "?" for _, _, t in cases]


def test_sql_case_quotes_strings_and_escapes():
    expr = codes.sql_case("x", {"1": "良", "2": "it's"}, "?")
    con = duckdb.connect()
    assert con.execute(f"SELECT {expr} FROM (SELECT '2' AS x)").fetchone()[0] == "it's"
    assert con.execute(f"SELECT {expr} FROM (SELECT '9' AS x)").fetchone()[0] == "?"
