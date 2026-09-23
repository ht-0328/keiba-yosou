"""合成DB の形が実DB と同じ約束（表名・列名・値の形）を守っていることを固定する。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from 合成DB import synth


def test_sample_db_has_tables_with_expected_columns(synth_db: Path):
    con = duckdb.connect(str(synth_db), read_only=True)
    names = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    assert set(synth.TABLES) <= names and {"_tables", "_meta"} <= names
    se_columns = [r[0] for r in con.execute("SELECT column_name FROM duckdb_columns() WHERE table_name = 'se' ORDER BY column_index").fetchall()]
    assert se_columns == list(synth.SE_COLUMNS)
    seq_type = con.execute("SELECT data_type FROM duckdb_columns() WHERE table_name = 'hr__単勝払戻' AND column_name = '_連番'").fetchone()[0]
    assert seq_type == "INTEGER"


def test_simple_race_values_follow_jvdata_widths():
    sample = synth.simple_race()
    favourite = sample.se[0]
    assert favourite["単勝人気順"] == "01" and favourite["単勝オッズ"] == "0020" and favourite["確定着順"] == "04"
    cancelled = sample.se[5]
    assert cancelled["異常区分コード"] == "1" and cancelled["単勝人気順"] == "00" and cancelled["単勝オッズ"] == "0000"
    assert sample.win[0]["払戻金"] == "000001500" and sample.win[0]["馬番"] == "04"
    assert [p["馬番"] for p in sample.place] == ["04", "02", "03"]


def test_build_db_can_omit_tables(tmp_path: Path):
    path = synth.build_db(tmp_path / "ra-only.duckdb", tables={"ra": synth.simple_race().ra})
    con = duckdb.connect(str(path), read_only=True)
    names = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    assert "ra" in names and "se" not in names
    assert con.execute("SELECT table_name FROM _tables").fetchall() == [("ra",)]


def test_odds_and_extra_payout_tables_follow_jvdata_widths(tmp_path: Path):
    """オッズの親と子（o1〜o6）とワイド・馬単の払戻は、行があるときだけ作られ、オッズは券種ごとの桁でゼロ埋めされる。"""
    sample = synth.simple_race()
    ra = sample.ra[0]
    sample.odds += [("o6", synth.odds_header(ra, "o6")), ("o6__3連単オッズ", synth.odds_row(ra, "o6__3連単オッズ", "040203", 123456, pop=250))]
    sample.odds.append(("o3__ワイドオッズ", synth.range_odds_row(ra, "o3__ワイドオッズ", "0204", 503, 538, pop=33)))
    sample.wide.append(synth.combo_payout(ra, "0204", 900, table="hr__ワイド払戻"))
    sample.exacta.append(synth.combo_payout(ra, "0402", 5600, table="hr__馬単払戻"))
    assert sample.odds[1][1]["オッズ"] == "0123456" and sample.odds[2][1]["最低オッズ"] == "00503"
    path = synth.build_db(tmp_path / "odds.duckdb", sample)
    con = duckdb.connect(str(path), read_only=True)
    names = {r[0] for r in con.execute("SELECT table_name FROM duckdb_tables()").fetchall()}
    assert {"o6", "o6__3連単オッズ", "o3__ワイドオッズ", "hr__ワイド払戻", "hr__馬単払戻"} <= names
    assert "o1" not in names and "o2__馬連オッズ" not in names
    header = con.execute("SELECT \"データ区分\", \"発表月日時分\" FROM o6").fetchone()
    assert header == ("5", "00000000")
    columns = [r[0] for r in con.execute("SELECT column_name FROM duckdb_columns() WHERE table_name = 'o3__ワイドオッズ' ORDER BY column_index").fetchall()]
    assert columns == list(synth.COMBO_RANGE_ODDS_COLUMNS)
