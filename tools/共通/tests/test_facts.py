"""事実表の契約: 列がそろう、無い表でも作れる、型変換と数え方の規則、前走、最新行。"""

from __future__ import annotations

from pathlib import Path

import pytest

from 合成DB import synth
from 共通 import db, facts


def _facts(con, where="TRUE", order="race_date, race_id, horse_no"):
    facts.ensure_facts(con)
    cursor = con.execute(f"SELECT * FROM facts WHERE {where} ORDER BY {order}")
    names = [d[0] for d in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def test_all_columns_exist_and_ensure_is_idempotent(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        assert facts.ensure_facts(con) == "facts" and facts.facts_ready(con)
        facts.ensure_facts(con)
        columns = {r[0] for r in con.execute("SELECT column_name FROM duckdb_columns() WHERE table_name = 'facts'").fetchall()}
    assert set(facts.FACT_COLUMNS) == columns


def test_conversions_and_counting_rules(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        rows = {r["horse_no"]: r for r in _facts(con)}
    assert len(rows) == 6
    favourite, winner, stopped, cancelled = rows[1], rows[4], rows[5], rows[6]
    assert favourite["popularity"] == 1 and favourite["win_odds"] == 2.0 and favourite["finish"] == 4 and favourite["ran"]
    assert favourite["win_payout"] == 0 and favourite["place_payout"] == 0 and favourite["abnormal_name"] == ""
    assert winner["finish"] == 1 and winner["win_payout"] == 1500 and winner["place_payout"] == 400 and winner["win_odds"] == 15.0
    assert rows[2]["place_payout"] == 180
    assert stopped["ran"] and stopped["finish"] is None and stopped["abnormal_name"] == "競走中止"
    assert not cancelled["ran"] and cancelled["popularity"] is None and cancelled["win_odds"] is None
    assert favourite["venue"] == "東京" and favourite["course"] == "芝・左" and favourite["surface"] == "芝"
    assert favourite["condition"] == "良" and favourite["class_name"] == "1勝クラス" and favourite["field_size"] == 5
    assert favourite["finish_time"] == 94.0 and favourite["last3f"] == 35.0  # 走破タイム '1340' = 1分34秒0
    assert favourite["body_weight"] == 480 and favourite["weight_change"] == 2
    assert favourite["sire"] == "父A" and favourite["grandsire"] == "父父A" and favourite["damsire"] == "母父A"
    assert favourite["dm_rank"] == 1 and favourite["tm_rank"] == 1 and favourite["tm_score"] == 80.0
    assert winner["tm_rank"] == 4 and rows[2]["sire"] is None
    assert favourite["mixed_sex"] is False and favourite["mixed_age"] is False
    assert favourite["race_id"] == "2024040605010101" and favourite["race_date"] == "2024-04-06" and favourite["month"] == 4


def test_builds_without_optional_tables(tmp_path: Path):
    sample = synth.simple_race()
    path = synth.build_db(tmp_path / "bare.duckdb", tables={"ra": sample.ra, "se": sample.se})
    with db.open_db(path) as con:
        rows = _facts(con)
    assert len(rows) == 6 and all(r["win_payout"] == 0 and r["sire"] is None and r["tm_rank"] is None for r in rows)


def test_condition_uses_dirt_for_dirt_courses(synth_db: Path):
    with db.open_db(synth_db) as con:
        rows = _facts(con, "horse_no = 1")
    by_race = {r["race_id"]: r for r in rows}
    dirt = by_race["2024040605010105"]
    assert dirt["surface"] == "ダート" and dirt["condition"] == "良" and dirt["course"] == "ダート・左"
    heavy = by_race["2024040706010103"]
    assert heavy["venue"] == "中山" and heavy["condition"] == "稍重" and heavy["course"] == "芝・右"


def test_previous_run_is_taken_from_this_horse_earlier_races(synth_db: Path):
    with db.open_db(synth_db) as con:
        rows = _facts(con, "horse_id = '2020000001'")
    assert [r["finish"] for r in rows] == [4, 1, 3, 2, 1, 4]
    assert rows[0]["prev_finish"] is None and rows[0]["interval_days"] is None
    assert rows[1]["prev_finish"] == 4 and rows[1]["interval_days"] == 0
    assert rows[-1]["prev_finish"] == 1 and rows[-1]["interval_days"] == 370 and rows[-1]["prev_popularity"] == 1


def test_latest_row_wins_over_entry_stage_rows(tmp_path: Path):
    sample = synth.simple_race()
    entry = synth.runner(sample.ra[0], 1, 1, 0, stage="2", odds="0000")
    sample.se.append(entry)
    path = synth.build_db(tmp_path / "dup.duckdb", sample)
    with db.open_db(path) as con:
        rows = _facts(con, "horse_no = 1")
    assert len(rows) == 1 and rows[0]["finish"] == 4 and rows[0]["win_odds"] == 2.0


def test_non_jra_and_unconfirmed_rows_are_excluded(tmp_path: Path):
    sample = synth.simple_race()
    sample.extend(synth.simple_race("20240406", "01", venue="30"))
    sample.extend(synth.simple_race("20240413", "01", stage="2"))
    path = synth.build_db(tmp_path / "mixed.duckdb", sample)
    with db.open_db(path) as con:
        rows = _facts(con)
    assert {r["race_id"] for r in rows} == {"2024040605010101"}


def test_rebuild_timing_reports_rows(one_race_db: Path):
    with db.open_db(one_race_db) as con:
        rows, elapsed = facts.rebuild_timing(con)
        table = facts.timing_table(con)
    assert rows == 6 and elapsed >= 0 and table.rows[1] == ["うち出走した行", 5]
    assert len(facts.columns_table().rows) == len(facts.FACT_COLUMNS)


def test_history_columns_use_only_earlier_races(synth_db: Path):
    """前走・累積・持ち時計は「今回より前」だけから作る。"""
    with db.open_db(synth_db) as con:
        horse1 = _facts(con, "horse_id = '2020000001'")
        horse4 = _facts(con, "horse_id = '2020000004'")
    last = horse1[-1]  # 2025-04-12 東京 芝・左 1600 良
    assert last["year"] == 2025 and last["runs_before"] == 5 and last["wins_before"] == 2 and last["lead_runs_before"] == 0
    assert last["course_runs_before"] == 3 and last["course_wins_before"] == 1
    assert last["best_time_unit"] == 94.0 and last["best_time_unit_rank"] == 1 and last["best_time_dist_rank"] == 1
    assert last["prev_style"] == "先行" and last["prev_last3f"] == 35.0 and last["prev_finish"] == 1
    assert last["jockey_change"] == "継続" and last["distance_change"] == "同じ" and last["class_change"] == "同級"
    assert last["venue_change"] == "別" and last["surface_change"] == "同じ"
    first = horse1[0]
    assert first["runs_before"] == 0 and first["prev_style"] is None and first["surface_change"] == "前走なし"
    assert first["best_time_unit"] is None and first["best_time_unit_rank"] is None and first["winner_style"] == "逃げ"
    dirt, after_dirt = horse1[2], horse1[3]
    assert dirt["surface_change"] == "芝→ダート" and after_dirt["surface_change"] == "ダート→芝"
    assert horse1[1]["winner_style"] == "先行"  # 1番人気が勝ったレース
    assert horse4[-1]["lead_runs_before"] == 5 and horse4[-1]["course_wins_before"] == 2 and horse4[-1]["prev_style"] == "逃げ"


def test_experience_columns_use_only_earlier_races(synth_db: Path):
    """同コース3着内・同競馬場勝利・同距離勝利・同馬場3着内・推定脚質も「今回より前」だけから作る。"""
    with db.open_db(synth_db) as con:
        horse1 = _facts(con, "horse_id = '2020000001'")
        horse4 = _facts(con, "horse_id = '2020000004'")
    last = horse1[-1]  # 2025-04-12 東京 芝・左 1600 良。それまで 東京芝 4,1,2着・東京ダ 3着・中山芝稍重 1着
    assert last["course_places_before"] == 2 and last["venue_wins_before"] == 1 and last["dist_wins_before"] == 2
    assert last["cond_places_before"] == 2 and last["style_before"] == "先行" and last["max_horse_no"] == 6
    assert last["same_race_runs_before"] is None  # 競走名の無い平場は、同レースを数えない
    first = horse1[0]
    assert first["style_before"] is None and first["course_places_before"] == 0 and first["lead_candidates"] == 0
    assert horse4[-1]["style_before"] == "逃げ" and horse4[-1]["lead_candidates"] == 1
    assert last["affiliation"] == "美浦" and last["blinker"] == "なし" and last["apprentice"] == "減量なし"


def test_same_race_experience_is_counted_by_race_name(trend_db: Path):
    with db.open_db(trend_db) as con:
        rows = _facts(con, "horse_id = '2020000004' AND race_name <> ''")
    assert [(r["same_race_runs_before"], r["same_race_wins_before"], r["same_race_places_before"]) for r in rows] == [(0, 0, 0), (1, 1, 1)]


def test_entry_facts_equal_facts_for_a_confirmed_race(synth_db: Path):
    """確定済みのレースに当てると、事実表のそのレースの行と同じになる（窓の定義が二重になっていない）。"""
    rid = "2025041205010101"
    with db.open_db(synth_db) as con:
        expected = _facts(con, f"race_id = '{rid}'")
        facts.build_entry_facts(con, facts.EntryScope(rid))
        cursor = con.execute(f"SELECT * FROM {facts.ENTRY_TABLE} ORDER BY horse_no")
        names = [d[0] for d in cursor.description]
        actual = [dict(zip(names, row)) for row in cursor.fetchall()]
    assert actual == expected and len(actual) == 6


def test_entry_facts_cover_an_unconfirmed_race(card_db: Path):
    """確定前のレースの出走馬にも、前走・累積の列が付く。結果の列は空。事実表そのものは変わらない。"""
    rid = "2025041905010102"  # 2025-04-19 東京 2R 出馬表
    with db.open_db(card_db) as con:
        facts.ensure_facts(con)
        before = con.execute("SELECT count(*) FROM facts").fetchone()[0]
        facts.build_entry_facts(con, facts.EntryScope(rid, "1"), popularity={1: 2}, weights={1: (486, 4)})
        cursor = con.execute(f"SELECT * FROM {facts.ENTRY_TABLE} ORDER BY horse_no")
        names = [d[0] for d in cursor.description]
        rows = {row["horse_no"]: row for row in (dict(zip(names, r)) for r in cursor.fetchall())}
        assert con.execute("SELECT count(*) FROM facts").fetchone()[0] == before
        with pytest.raises(ValueError):
            facts.build_entry_facts(con, facts.EntryScope(rid), popularity={99: 1})
        with pytest.raises(LookupError):
            facts.build_entry_facts(con, facts.EntryScope("2030010105010101"))
    assert set(rows) == {1, 2, 3, 4, 5, 7} and set(names) == set(facts.FACT_COLUMNS)
    old, debut = rows[1], rows[7]
    assert old["runs_before"] == 6 and old["prev_finish"] == 4 and old["interval_days"] == 7 and old["course_runs_before"] == 4
    assert old["condition"] == "良" and old["best_time_unit"] == 94.0 and old["field_size"] == 6 and old["finish"] is None and old["ran"]
    assert old["popularity"] == 2 and old["body_weight"] == 486 and old["weight_change"] == 4 and rows[2]["popularity"] is None
    assert debut["runs_before"] == 0 and debut["style_before"] is None and debut["surface_change"] == "前走なし"


def test_entry_condition_is_null_until_given_and_stage1_has_no_numbers(card_db: Path):
    with db.open_db(card_db) as con:
        facts.build_entry_facts(con, facts.EntryScope("2025041905010101"))  # 1R は出走馬名表（枠番・馬番が未定）
        rows = con.execute(f"SELECT horse_no, frame_no, condition_code, best_time_unit FROM {facts.ENTRY_TABLE}").fetchall()
        with pytest.raises(ValueError):
            facts.build_entry_facts(con, facts.EntryScope("2025041905010101"), popularity={1: 1})
    assert len(rows) == 6 and all(row == (None, None, None, None) for row in rows)
    with pytest.raises(ValueError):
        facts.EntryScope("2025041905010101", "9")
    with pytest.raises(ValueError):
        facts.EntryScope("123")


def test_entry_facts_drop_horses_missing_from_the_newest_stage(tmp_path: Path):
    """出走馬名表にだけ居て、出馬表で消えた馬は拾わない。"""
    sample = synth.simple_race()
    card = synth.card_race("20250419", "02", stage="2")
    ghost = synth.runner(card.ra[0], 9, 0, 0, stage="1", hid="2020000009", odds="0000", style="0", **{"枠番": "0", "馬番": "00"})
    card.se.append(ghost)
    path = synth.build_db(tmp_path / "ghost.duckdb", sample.extend(card))
    with db.open_db(path) as con:
        facts.build_entry_facts(con, facts.EntryScope("2025041905010102"))
        ids = {r[0] for r in con.execute(f"SELECT horse_id FROM {facts.ENTRY_TABLE}").fetchall()}
    assert "2020000009" not in ids and len(ids) == 6
