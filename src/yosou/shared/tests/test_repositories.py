"""SQL のリポジトリ（1 SQL につき 1 クラス）が、元DB から正しく読めること。"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from 共通 import db
from 合成DB import synth

from ..repository import (
    AnnouncedGoingRepository,
    AnnouncedWeightRepository,
    CareerCountRepository,
    EntryRepository,
    FactTableRepository,
    PastRunRepository,
    PeopleDayRepository,
    RaceEntryTableRepository,
    ScratchRepository,
    TargetScope,
    WorkoutRepository,
)
from . import synthetic_season as season

SINCE_2024 = TargetScope.since(date(2024, 1, 1))


@pytest.fixture(scope="module")
def season_con(season_db: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """架空の1シーズンの合成DB への接続（事実表つき）。"""
    with db.open_db(season_db) as con:
        FactTableRepository(con).ensure()
        yield con


def test_entries_are_read_in_date_order(season_con):
    entries = EntryRepository(season_con).read(SINCE_2024)
    assert entries["race_date"].min() >= pd.Timestamp("2024-01-01")
    assert entries["race_date"].is_monotonic_increasing
    assert {"race_id", "horse_id", "ran", "finish", "sire", "lead_candidates"} <= set(entries.columns)


def test_career_counts_follow_the_race_conditions(tmp_path: Path):
    # 東京 ダ1400 稍重のレース。紛らわしい欄（東京芝・ダ1401-1600・ダ良）にも数を入れておく
    sample = synth.simple_race("20240406", "01", track="23", distance="1400", turf="0", dirt="2")
    horse = sample.se[0]["血統登録番号"]
    sample.ck.append(synth.ck(sample.ra[0], horse, {
        "中央合計着回数": (1, 2, 0, 1, 0, 6),
        "東京ダ・着回数": (1, 0, 1, 0, 0, 1), "東京芝・着回数": (0, 0, 0, 0, 0, 9),
        "ダ1201-1400・着回数": (0, 1, 0, 0, 0, 2), "ダ1401-1600・着回数": (5, 0, 0, 0, 0, 0),
        "ダ稍・着回数": (0, 0, 1, 0, 1, 0), "ダ良・着回数": (7, 0, 0, 0, 0, 0),
    }))
    with db.open_db(synth.build_db(tmp_path / "ck.duckdb", sample)) as con:
        FactTableRepository(con).ensure()
        counts = CareerCountRepository(con).read(SINCE_2024)
    assert counts["horse_id"].tolist() == [horse]
    row = counts.iloc[0]
    assert (row["ck_total_runs"], row["ck_total_wins"], row["ck_total_places"]) == (10, 1, 3)
    assert (row["ck_venue_runs"], row["ck_venue_places"]) == (3, 2)
    assert (row["ck_band_runs"], row["ck_band_places"]) == (3, 1)
    assert (row["ck_going_runs"], row["ck_going_places"]) == (2, 1)


def test_career_totals_match_the_runs_before_each_race(season_con):
    # 合成のシーズンの出走別着度数は、シーズンの初めからの通算。DB にある過去走の数と一致する
    entries = EntryRepository(season_con).read(SINCE_2024)
    counts = CareerCountRepository(season_con).read(SINCE_2024)
    runs = PastRunRepository(season_con).read(SINCE_2024)
    checked = entries.merge(counts, on=["race_id", "horse_id"]).head(300)
    rows = checked[["horse_id", "race_date", "ck_total_runs"]].itertuples(index=False)
    for horse_id, race_day, total in rows:
        is_earlier_run = (runs["horse_id"] == horse_id) & (runs["race_date"] < race_day)
        assert total == is_earlier_run.sum()


def test_workouts_are_within_14_days_before_some_race(season_con):
    entries = EntryRepository(season_con).read(SINCE_2024)
    workouts = WorkoutRepository(season_con, window_days=14).read(SINCE_2024)
    race_days = entries[["horse_id", "race_date"]].drop_duplicates()
    sessions = workouts.merge(race_days, on="horse_id")
    days_before = (sessions["race_date"] - sessions["work_date"]).dt.days
    sessions["is_in_window"] = days_before.between(1, 14)
    assert sessions.groupby(["horse_id", "work_date", "work_time"])["is_in_window"].any().all()
    assert set(workouts["course"]) == {"坂路", "ウッド"}


def test_people_days_cover_the_window_before_the_first_race(season_con):
    scope = TargetScope.since(date(2024, 6, 1))
    jockey_days = PeopleDayRepository.for_jockeys(season_con, window_days=365).read(scope)
    trainer_days = PeopleDayRepository.for_trainers(season_con, window_days=365).read(scope)
    assert jockey_days["race_date"].min() >= pd.Timestamp("2023-06-02")
    assert jockey_days["race_date"].max() < pd.Timestamp("2024-12-28")
    assert trainer_days["places"].le(trainer_days["starts"]).all()
    assert jockey_days["person_code"].nunique() == 12 and trainer_days["person_code"].nunique() == 7


def test_announced_going_is_the_last_report_for_the_track(season_con):
    assert AnnouncedGoingRepository(season_con).read(season.CARD_RACE_ID) == season.ANNOUNCED_TURF_GOING
    assert AnnouncedGoingRepository(season_con).read("2024122805010101") is None


def test_announced_weights_have_signed_changes(season_con):
    weights = AnnouncedWeightRepository(season_con).read(season.CARD_RACE_ID).set_index("horse_no")
    assert list(weights.index) == [1, 2, 3, 4, 5, 6, 7]
    assert (weights.loc[3, "body_weight"], weights.loc[3, "weight_change"]) == (473, -3)
    assert (weights.loc[4, "body_weight"], weights.loc[4, "weight_change"]) == (474, 4)
    assert AnnouncedWeightRepository(season_con).read(season.ENTRY_LIST_RACE_ID).empty


def test_scratches_list_horse_numbers(season_con):
    assert ScratchRepository(season_con).read(season.CARD_RACE_ID) == [season.SCRATCHED_HORSE_NO]
    assert ScratchRepository(season_con).read(season.ENTRY_LIST_RACE_ID) == []


def test_race_entry_table_uses_the_given_going(season_con):
    scope = RaceEntryTableRepository(season_con).build(season.CARD_RACE_ID, going_code="3")
    entries = EntryRepository(season_con).read(scope)
    assert len(entries) == 8 and set(entries["condition"]) == {"重"}


def test_race_entry_table_of_entry_list_has_no_horse_numbers(season_con):
    scope = RaceEntryTableRepository(season_con).build(season.ENTRY_LIST_RACE_ID, going_code=None)
    entries = EntryRepository(season_con).read(scope)
    assert len(entries) == 8 and entries["horse_no"].isna().all() and entries["ran"].all()


def test_race_entry_table_reports_unknown_race(season_con):
    with pytest.raises(LookupError):
        RaceEntryTableRepository(season_con).build("2025011105010109", going_code=None)
    with pytest.raises(ValueError):
        RaceEntryTableRepository(season_con).build("20250111", going_code=None)


def test_db_without_optional_tables_still_reads(tmp_path: Path):
    # 出走別着度数・調教・速報の表が無い DB（取得する前の状態）
    with db.open_db(synth.sample_db(tmp_path / "sample.duckdb")) as con:
        FactTableRepository(con).ensure()
        race_id = EntryRepository(con).read(SINCE_2024)["race_id"].iloc[0]
        assert CareerCountRepository(con).read(SINCE_2024).empty
        assert WorkoutRepository(con, window_days=14).read(SINCE_2024).empty
        assert AnnouncedGoingRepository(con).read(race_id) is None
        assert AnnouncedWeightRepository(con).read(race_id).empty
        assert ScratchRepository(con).read(race_id) == []
