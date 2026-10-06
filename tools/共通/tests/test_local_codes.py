"""地方のコード値と事実表の決めごと（クラスの読み取り・元データの見分け・地方の事実表）。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from 共通 import db, facts, local_codes
from 合成DB import local_synth

#: 競走条件名称とグレードコード → クラス名（設計書「地方競馬の近走と適性から3着以内を予想」06 の図2）。
CASES: tuple[tuple[str, str, str], ...] = (
    ("３歳上Ｃ３　二", "", "C3"), ("Ｂ１－２", "", "B1"), ("Ｃ －１２", "", "C"), ("　　　Ｃ２　九　Ｃ２　十", "", "C2"),
    ("Ｂ３　三　選抜", "", "B3"), ("Ａ　Ｂ", "", "A"), ("Ｃ５－１", "", "C4"),
    ("ＪＲＡ認定　２歳　新馬", "", "新馬"), ("２歳　初出走", "", "新馬"), ("２歳　認未勝", "", "未勝利"), ("３歳　未勝利", "", "未勝利"),
    ("ＪＲＡ認定　３歳　Ｃ１", "", "C1"), ("３歳上ＯＰ", "", "オープン"), ("３歳　一　二", "", "年齢の条件戦"),
    ("　", "", "条件不明"), ("農林水産大臣賞典", "A", "Jpn1"), ("", "B", "Jpn2"), ("", "C", "Jpn3"),
    ("Ｓ１", "P", "重賞"), ("", "S", "重賞"), ("Ｂ１", "T", "準重賞"), ("Ｂ１　特別", "E", "B1"),
)


@pytest.mark.parametrize("name,grade,expected", CASES)
def test_local_class_name(name: str, grade: str, expected: str):
    assert local_codes.local_class_name(name, grade) == expected


def test_sql_and_python_agree_on_every_case():
    con = duckdb.connect()
    con.register("cases", __import__("pandas").DataFrame(CASES, columns=["name", "grade", "expected"]))
    sql = local_codes.local_class_name_sql("name", "grade")
    rows = con.execute(f"SELECT name, grade, expected, {sql} FROM cases").fetchall()
    assert all(got == expected for _, _, expected, got in rows), rows


def test_every_class_name_has_an_order():
    names = {expected for _, _, expected in CASES} - {"条件不明"}
    assert names <= set(local_codes.LOCAL_CLASS_ORDER)
    # 格の並びは C < B < A < オープン < 準重賞 < 重賞 < Jpn
    order = local_codes.LOCAL_CLASS_ORDER
    assert order["C1"] < order["B3"] < order["B1"] < order["A3"] < order["A1"] < order["オープン"] < order["準重賞"] < order["重賞"] < order["Jpn3"]
    assert order["C"] == order["C2"] and order["B"] == order["B2"] and order["A"] == order["A2"]


def test_detect_source_by_the_local_master_table():
    con = duckdb.connect()
    assert facts.detect_source(con) is facts.JRA_FACTS_SOURCE
    con.execute("CREATE TABLE nu (血統登録番号 VARCHAR)")
    assert facts.detect_source(con) is local_codes.LOCAL_FACTS_SOURCE
    assert local_codes.LOCAL_FACTS_SOURCE.venue_filter("r") == 'r."競馬場コード" BETWEEN \'30\' AND \'61\''


def test_local_facts_read_venue_class_and_pedigree(tmp_path: Path):
    path = local_synth.local_db(tmp_path / "local.duckdb")
    with db.open_db(path) as con:
        facts.ensure_facts(con)
        rows = con.execute(
            "SELECT DISTINCT venue, class_name, class_order, affiliation, sire FROM facts WHERE ran ORDER BY class_order"
        ).fetchall()
    venues = {venue for venue, *_ in rows}
    classes = {(class_name, class_order) for _, class_name, class_order, _, _ in rows}
    assert venues == {"大井"} and {"招待"} == {affiliation for *_, affiliation, _ in rows}
    assert classes == {("C2", 5), ("B1", 10), ("オープン", 15)}
    assert {sire for *_, sire in rows} <= {"父0", "父1"}


def test_local_venue_code_accepts_name_and_code():
    assert local_codes.local_venue_code("大井") == "44" and local_codes.local_venue_code("44") == "44"
    with pytest.raises(ValueError):
        local_codes.local_venue_code("東京")
    assert "83" not in local_codes.LOCAL_VENUE_NAMES
