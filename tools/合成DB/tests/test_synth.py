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
