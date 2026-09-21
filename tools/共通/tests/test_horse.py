"""馬の検索・プロフィール・過去走の契約。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 合成DB import synth
from 共通 import db, horse


def test_find_horses_prefers_prefix_match(synth_db: Path):
    with db.open_db(synth_db) as con:
        found = horse.find_horses(con, "ウマ0")
        one = horse.find_horses(con, "ウマ01")
        with pytest.raises(ValueError):
            horse.find_horses(con, "  ")
    assert found.columns[:2] == ["hid", "馬名"] and len(found.rows) == 6
    assert one.rows[0][0] == "2020000001" and one.rows[0][5] == "父A"


def test_profile_and_runs(synth_db: Path):
    with db.open_db(synth_db) as con:
        profile = horse.horse_profile(con, "2020000001")
        runs = horse.horse_runs(con, "2020000001")
        before = horse.horse_runs(con, "2020000001", before="2025-04-12")
        with pytest.raises(LookupError):
            horse.horse_profile(con, "2099000001")
        with pytest.raises(ValueError):
            horse.horse_profile(con, "abc")
    assert profile["馬名"] == "ウマ01" and profile["父"] == "父A" and profile["母父"] == "母父A" and profile["生年月日"] == "2020-04-01"
    assert horse.profile_table(profile).title == "ウマ01（2020000001）"
    assert len(runs.rows) == 6 and runs.rows[0][0] == "2025-04-12" and runs.columns[-1] == "rid"
    assert len(before.rows) == 5 and before.rows[0][0] == "2024-04-07" and "より前" in before.note


def test_falls_back_to_facts_without_um(tmp_path: Path):
    sample = synth.simple_race()
    path = synth.build_db(tmp_path / "noum.duckdb", tables={"ra": sample.ra, "se": sample.se})
    with db.open_db(path) as con:
        found = horse.find_horses(con, "ウマ04")
        profile = horse.horse_profile(con, "2020000004")
    assert found.rows[0][0] == "2020000004" and profile["馬名"] == "ウマ04" and profile["父"] is None
