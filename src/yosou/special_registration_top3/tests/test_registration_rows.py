"""登録馬の行の一時表（設計書 06 の図2・11 の 7）。合成DB の特別登録で確かめる。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from 共通 import db, facts

from yosou.shared.repository.target_scope import AS_OF_COLUMN
from yosou.shared.tests import synthetic_season as season

from ..dataset import RegistrationCutoff
from ..repository import TABLE, RegistrationEntryInfoRepository, RegistrationEntryTableRepository, RegistrationListRepository, RegistrationRaceRepository


def _entries(con: duckdb.DuckDBPyConnection, race_id: str) -> pd.DataFrame:
    scope = RegistrationEntryTableRepository(con, RegistrationCutoff().sql("race_date")).build(race_id)
    assert scope.as_of_column == AS_OF_COLUMN
    return con.execute(f"SELECT * FROM {scope.relation} ORDER BY horse_id").df()


def test_the_registration_only_race_gets_rows_for_every_registered_horse(season_db: Path):
    with db.open_db(season_db) as con:
        facts.ensure_facts(con)
        rows = _entries(con, season.REGISTRATION_ONLY_RACE_ID)
    assert len(rows) == season.REGISTRATION_ONLY_FIELD_SIZE
    # 出走するとみなす。馬番・枠番・騎手・馬体重・オッズ・着順は無い。競走名が付き、締めの日は開催日より前の直近の月曜
    assert rows["ran"].all() and rows["horse_no"].isna().all() and rows["frame_no"].isna().all()
    assert rows["jockey_code"].isna().all() and rows["body_weight"].isna().all() and rows["win_odds"].isna().all()
    assert rows["finish"].isna().all() and rows["abnormal_name"].eq("").all()
    assert (rows["race_name"] == season.REGISTRATION_RACE_NAME).all()
    assert set(pd.to_datetime(rows[AS_OF_COLUMN]).dt.date) == {RegistrationCutoff().of(season.FUTURE_DAY)}
    # 馬齢は血統登録番号の生年から（2020年生まれ → 2025年は 5歳）。負担重量・調教師・所属は登録から
    assert (rows["age"] == 5).all() and (rows["carried"] == 57.0).all() and rows["trainer_code"].notna().all()
    assert set(rows["affiliation"]) == {"美浦"}
    # 事実表と同じ列が付く（前走・通算の出走数）。シーズンを走った馬なので過去走がある
    assert (rows["runs_before"] > 0).all() and rows["prev_finish"].notna().all()


def test_the_entry_list_race_uses_the_registration_not_the_entry_list(season_db: Path):
    with db.open_db(season_db) as con:
        facts.ensure_facts(con)
        rows = _entries(con, season.ENTRY_LIST_RACE_ID)
        listed = con.execute(f"SELECT count(*) FROM se WHERE {facts.keys.rid_expr()} = ?", [season.ENTRY_LIST_RACE_ID]).fetchone()[0]
        info = RegistrationEntryInfoRepository(con).read(season.ENTRY_LIST_RACE_ID)
    # 出走馬名表には8頭、特別登録には9頭（地方馬1頭が多い）。登録馬の行は登録から作る
    assert listed == season.FUTURE_FIELD_SIZE and len(rows) == season.FUTURE_FIELD_SIZE + 1
    assert rows["jockey_code"].isna().all()
    assert len(info) == season.FUTURE_FIELD_SIZE + 1 and (info["交流区分"] == "地方").sum() == 1


def test_a_race_without_registration_stops_with_the_fetch_guidance(season_db: Path):
    with db.open_db(season_db) as con:
        facts.ensure_facts(con)
        with pytest.raises(LookupError, match="TOKU"):
            RegistrationEntryTableRepository(con, RegistrationCutoff().sql("race_date")).build(season.CARD_RACE_ID)


def test_registered_races_can_be_listed_and_resolved(season_db: Path):
    with db.open_db(season_db) as con:
        races = RegistrationListRepository(con).read(season.FUTURE_DAY, season.FUTURE_DAY)
        rid = RegistrationRaceRepository(con).resolve(season.FUTURE_DAY.isoformat(), season.VENUE_NAME, 4)
        with pytest.raises(LookupError):
            RegistrationRaceRepository(con).resolve(season.FUTURE_DAY.isoformat(), season.VENUE_NAME, 1)
    assert list(races["race_id"]) == [season.ENTRY_LIST_RACE_ID, season.REGISTRATION_ONLY_RACE_ID]
    assert list(races["entries"]) == [season.FUTURE_FIELD_SIZE + 1, season.REGISTRATION_ONLY_FIELD_SIZE]
    assert rid == season.REGISTRATION_ONLY_RACE_ID
    assert TABLE == "yosou_registration_entries"
