"""表の閲覧と DB の状態の契約。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 共通 import browse, db


def test_names_hide_internal_tables(synth_db: Path):
    with db.open_db(synth_db) as con:
        names = browse.TableBrowser(con).names()
    assert "ra" in names and "hr__単勝払戻" in names and not any(n.startswith("_") for n in names)


def test_describe_works_before_titles_are_cached(synth_db: Path):
    """表題をまだ読んでいない閲覧器でも、列の一覧が返る（表題の読み出しで結果が入れ替わらない）。"""
    with db.open_db(synth_db) as con:
        described = browse.TableBrowser(con).describe("se")
    assert described.columns == ["番号", "列", "型"] and described.title == "se（馬毎レース情報）の列"
    assert any(row[1] == "馬番" for row in described.rows)


def test_titles_and_describe(synth_db: Path):
    with db.open_db(synth_db) as con:
        b = browse.TableBrowser(con)
        assert b.title("ra") == "レース詳細" and b.title("hr__単勝払戻") == "払戻 › 単勝払戻"
        described = b.describe("hr__単勝払戻")
        assert described.columns == ["番号", "列", "型"] and any(row[1] == "_連番" and row[2] == "INTEGER" for row in described.rows)
        with pytest.raises(LookupError):
            b.columns("nope")


def test_list_tables_counts_rows_in_range(synth_db: Path):
    with db.open_db(synth_db) as con:
        infos = {i.name: i for i in browse.TableBrowser(con).list_tables("2024-04-07", "2024-04-07")}
    assert infos["ra"].rows == 6 and infos["ra"].rows_in_range == 2
    assert infos["ra"].date_from == "2024-04-06" and infos["ra"].date_to == "2025-04-12"
    assert infos["um"].rows_in_range is None and infos["um"].date_from is None


def test_read_limits_columns_rows_and_filters(synth_db: Path):
    with db.open_db(synth_db) as con:
        b = browse.TableBrowser(con)
        result = b.read("se", limit=500, max_rows=4, equals={"競馬場コード": "05", "レース番号": "01"}, date_from="2024-04-06", date_to="2024-04-06")
        assert result["total"] == 6 and len(result["rows"]) == 4 and result["limit"] == 4
        assert result["columns"][:3] == ["レコード種別ID", "データ区分", "データ作成年月日"]
        chosen = b.read("se", columns=["馬番", "馬名"], limit=2)
        assert chosen["columns"] == ["馬番", "馬名"] and chosen["rows"][0][0] == "01"
        with pytest.raises(LookupError):
            b.read("se", equals={"存在しない列": "1"})
        with pytest.raises(LookupError):
            b.read("se", columns=["存在しない列"])
        table = browse.rows_table(chosen)
        assert "全 36 行のうち 1〜2 行" in table.note


def test_db_status_reports_final_range_and_optional_tables(synth_db: Path):
    with db.open_db(synth_db) as con:
        status = browse.db_status(con, synth_db)
    assert status.race_range == ("2024-04-06", "2025-04-12")
    assert status.final_races == 6 and status.final_runs == 30
    assert status.optional_from["対戦型マイニング予想"] == "2024-04-06" and status.optional_from["出走別着度数"] is None
    assert status.meta == {"sync:RACE": "20260912000000"}
    rows = dict((r[0], r[1]) for r in browse.status_table(status).rows)
    assert rows["表の数"] == 9 and rows["出走別着度数 の最初の開催日"] == "（表が無い）"


def test_parse_equals():
    assert browse.parse_equals(["a=1", "b=x=y"]) == {"a": "1", "b": "x=y"}
    with pytest.raises(ValueError):
        browse.parse_equals(["novalue"])
