"""特別登録から登録馬の行（ra・se と同じ列）を作る SQL（registration.py）と、事実表の SQL が ra・se の代わりに読む関係（EntryRows）。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from 共通 import facts, keys, registration
from 合成DB import synth

#: 合成DB の確定成績のあとの日に、特別登録だけがあるレース（2024-04-13 東京 7R）。
_DAY, _NO = "20240413", "07"
_RID = f"{_DAY}050101{_NO}"


def _registration_db(path: Path, *, with_entry_list: bool = False, stages: tuple[str, ...] = ("2",)) -> Path:
    """確定成績（``sample``）に、登録馬3頭（うち1頭は初出走の地方馬）の特別登録を足した合成DB。

    ``with_entry_list`` なら、同じレースの出走馬名表（別の2頭）も入れる（登録からだけ行を作ることを確かめる）。
    ``stages`` は入れる版（1 日曜・2 月曜）。
    """
    rows = synth.sample()
    for stage in stages:
        rows.registrations.append(synth.registration(_DAY, _NO, name="合成登録特別", stage=stage, entries="03",
                                                     created=f"2024040{6 if stage == '1' else 7}"))
    # 登録馬の子表は版を持たないので、1組だけ（実DB も鍵ごとに最新の版だけを持つ）。日曜の版だけならハンデの負担重量は 000
    handicap = "2" in stages
    registration = rows.registrations[-1]
    rows.registered_horses.extend([
        synth.registered_horse(registration, 1, "2020000001", "ウマ01", carried="570" if handicap else "000"),
        synth.registered_horse(registration, 2, "2020000004", "ウマ04", carried="550" if handicap else "000", sex="2"),
        synth.registered_horse(registration, 3, "2019000099", "チホウ", carried="560" if handicap else "000", area="3", exchange="1"),
    ])
    if with_entry_list:
        race = synth.race(_DAY, _NO, stage="1", name="合成登録特別", field_size="00", entries="02")
        rows.ra.append(race)
        rows.se.extend([synth.runner(race, 1, 0, 0, hid="2020000002", odds="0000", **{"枠番": "0", "馬番": "00"}),
                        synth.runner(race, 2, 0, 0, hid="2020000003", odds="0000", **{"枠番": "0", "馬番": "00"})])
    return synth.build_db(path, rows)


def _entry_rows(path: Path) -> list[tuple]:
    con = duckdb.connect(str(path))
    try:
        facts.build_entry_facts(con, facts.EntryScope(_RID), name="reg", rows=registration.registration_rows_sql(con, _RID))
        return con.execute(
            "SELECT horse_id, age, sex, carried, affiliation, ran, horse_no, jockey_code, finish, race_name, runs_before, blinker, apprentice "
            "FROM reg ORDER BY horse_id"
        ).fetchall()
    finally:
        con.close()


def test_registration_rows_get_the_facts_columns_without_entry_list_values(tmp_path: Path):
    rows = _entry_rows(_registration_db(tmp_path / "reg.duckdb"))
    assert [row[0] for row in rows] == ["2019000099", "2020000001", "2020000004"]
    local, first, fourth = rows
    # 馬齢は生年から（2024年: 2019年生まれは 5歳、2020年生まれは 4歳）。性別・負担重量・所属は登録から
    assert (first[1], first[2], first[3], first[4]) == (4, "牡", 57.0, "美浦")
    assert (fourth[1], fourth[2], fourth[3]) == (5 - 1, "牝", 55.0)
    assert (local[1], local[4]) == (5, "招待")
    # 出走するとみなし、馬番・騎手・着順は無い。競走名は登録のもの。ブリンカー・減量は「なし」
    assert all(row[5] for row in rows) and all(row[6] is None and row[7] is None and row[8] is None for row in rows)
    assert all(row[9] == "合成登録特別" for row in rows) and all(row[11] == "なし" and row[12] == "減量なし" for row in rows)
    # 確定成績のある馬は過去走が数えられ、初出走の地方馬は 0
    assert first[10] > 0 and fourth[10] > 0 and local[10] == 0


def test_registration_rows_ignore_the_entry_list_of_the_same_race(tmp_path: Path):
    rows = _entry_rows(_registration_db(tmp_path / "reg.duckdb", with_entry_list=True))
    assert [row[0] for row in rows] == ["2019000099", "2020000001", "2020000004"]


def test_the_monday_version_is_preferred_over_the_sunday_version(tmp_path: Path):
    rows = _entry_rows(_registration_db(tmp_path / "reg.duckdb", stages=("1", "2")))
    assert [row[3] for row in rows] == [56.0, 57.0, 55.0]
    # 日曜の版だけなら、ハンデの負担重量（000）は欠損値
    sunday = _entry_rows(_registration_db(tmp_path / "sun.duckdb", stages=("1",)))
    assert [row[3] for row in sunday] == [None, None, None]


def test_without_registration_the_entry_table_is_not_found(tmp_path: Path):
    path = synth.sample_db(tmp_path / "plain.duckdb")
    con = duckdb.connect(str(path))
    try:
        with pytest.raises(LookupError):
            facts.build_entry_facts(con, facts.EntryScope(_RID), name="reg", rows=registration.registration_rows_sql(con, _RID))
    finally:
        con.close()


def test_the_default_entry_rows_are_ra_and_se():
    assert facts.EntryRows() == facts.EntryRows(race="ra", runner="se")
    rows = registration.registration_rows_sql(duckdb.connect(), _RID)
    assert "UNION ALL BY NAME" in rows.race and keys.q("血統登録番号") in rows.runner and _NO in rows.race
