"""まとまり Q（勝ち切る材料）の読み方と作り方。合成DB と手で作った記録だけを使う。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from 共通 import facts
from 合成DB import synth

from ..dataset import FinishRecordsLoader
from ..feature import FINISH_POWER_FEATURES, FINISH_POWER_NAMES, EntryRecords, WorkoutCoverage
from ..feature.group import FinishPowerFeatures
from ..repository import HORSE_FINISH_NAMES, PEOPLE_FINISH_NAMES, HorseFinishRepository, PeopleFinishRepository, TargetScope


def _two_weeks_db(tmp_path: Path) -> duckdb.DuckDBPyConnection:
    """同じ馬が 2024-04-06 と 2024-04-13 に走った2レースの合成DB（1番人気 4着・2番人気 2着・3番人気 3着・4番人気 1着）。"""
    sample = synth.simple_race(day="20240406").extend(synth.simple_race(day="20240413"))
    con = duckdb.connect(str(synth.build_db(tmp_path / "finish.duckdb", sample)), read_only=True)
    facts.ensure_facts(con)
    return con


def test_the_ten_features_are_numbers_in_group_q_known_from_thursday():
    assert [feature.name for feature in FINISH_POWER_FEATURES] == list(FINISH_POWER_NAMES) == list(HORSE_FINISH_NAMES + PEOPLE_FINISH_NAMES)
    assert len(FINISH_POWER_NAMES) == 10
    assert all(feature.group == "Q" and feature.known_from.value == "thursday" for feature in FINISH_POWER_FEATURES)


def test_horse_finish_counts_only_the_runs_before_the_race(tmp_path: Path):
    con = _two_weeks_db(tmp_path)
    table = HorseFinishRepository(con).read(TargetScope.since(pd.Timestamp("2024-01-01").date()))
    first = table[table["race_id"].str.startswith("20240406")].set_index("horse_id")
    second = table[table["race_id"].str.startswith("20240413")].set_index("horse_id")
    wins, seconds, rate, near, margin, lost = HORSE_FINISH_NAMES
    assert (first[wins] == 0).all() and first[rate].isna().all() and first[margin].isna().all()  # 最初の出走には過去走が無い
    winner, runner_up, favorite = "2020000004", "2020000002", "2020000001"
    assert second.loc[winner, wins] == 1 and second.loc[winner, rate] == pytest.approx(1.0) and second.loc[winner, margin] == pytest.approx(0.0)
    assert second.loc[runner_up, seconds] == 1 and second.loc[runner_up, rate] == pytest.approx(0.0)
    assert second.loc[runner_up, near] == 1 and second.loc[runner_up, lost] == 1  # 2番人気で 0.2秒差の2着
    assert second.loc[favorite, lost] == 1 and second.loc[favorite, near] == 0  # 1番人気で 0.6秒差の4着
    assert list(table.columns) == ["race_id", "horse_id", *HORSE_FINISH_NAMES]
    # 対象を2つ目のレースだけにしても、過去走は事実表の全部から数える
    only_second = HorseFinishRepository(con).read(TargetScope(f"(SELECT * FROM {facts.FACTS_TABLE} WHERE race_date = '2024-04-13')"))
    assert only_second.set_index("horse_id").loc[winner, wins] == 1 and len(only_second) == len(second)


def test_people_finish_shrinks_small_counts_and_excludes_the_race_day(tmp_path: Path):
    con = _two_weeks_db(tmp_path)
    table = PeopleFinishRepository(con).read(TargetScope.since(pd.Timestamp("2024-01-01").date()))
    first = table[table["race_id"].str.startswith("20240406")].set_index("horse_id")
    second = table[table["race_id"].str.startswith("20240413")].set_index("horse_id")
    jockey_rate, jockey_favorite, trainer_rate, trainer_favorite = PEOPLE_FINISH_NAMES
    assert first[jockey_rate].tolist() == pytest.approx([0.5] * len(first))  # 記録が無ければ全体の値
    assert first[jockey_favorite].tolist() == pytest.approx([0.33] * len(first))
    # 勝ち馬の騎手D: 1年で 1勝 0回の2着 → (1 + 10) ÷ (1 + 20)。1番人気には乗っていない → 0.33 のまま
    assert second.loc["2020000004", jockey_rate] == pytest.approx(11 / 21) and second.loc["2020000004", jockey_favorite] == pytest.approx(0.33)
    # 1番人気に乗った騎手A は負けた → (0 + 6.6) ÷ (1 + 20)
    assert second.loc["2020000001", jockey_favorite] == pytest.approx(6.6 / 21)
    # 調教師は全頭同じ: 1勝・1回の2着 → 11 ÷ 22、1番人気 1回で負け
    assert second[trainer_rate].tolist() == pytest.approx([0.5] * len(second))
    assert second[trainer_favorite].tolist() == pytest.approx([6.6 / 21] * len(second))
    assert list(table.columns) == ["race_id", "horse_id", *PEOPLE_FINISH_NAMES]


def test_the_loader_joins_the_horse_and_people_columns(tmp_path: Path):
    con = _two_weeks_db(tmp_path)
    records = FinishRecordsLoader(con).read(TargetScope.since(pd.Timestamp("2024-01-01").date()))
    assert set(records.columns) == {"race_id", "horse_id", *FINISH_POWER_NAMES}
    assert len(records) == 12  # 2レース × 6頭（出走取消の馬も対象に入り、行を選ぶ段で落ちる）


def _records(finish_records: pd.DataFrame) -> EntryRecords:
    entries = pd.DataFrame({"race_id": ["r1", "r1", "r1"], "horse_id": ["a", "b", "c"]})
    return EntryRecords(
        entries=entries, past_runs=pd.DataFrame(), workouts=pd.DataFrame(), workout_coverage=WorkoutCoverage.complete(),
        jockey_days=pd.DataFrame(), trainer_days=pd.DataFrame(), sire_days=pd.DataFrame(), damsire_days=pd.DataFrame(),
        finish_records=finish_records,
    )


def test_finish_power_features_align_to_the_entries_and_are_missing_without_records():
    records = pd.DataFrame({"race_id": ["r1", "r1"], "horse_id": ["b", "a"], **{name: [2.0, 1.0] for name in FINISH_POWER_NAMES}})
    features = FinishPowerFeatures().build(_records(records))
    assert list(features.columns) == list(FINISH_POWER_NAMES)
    assert features.iloc[0, 0] == 1.0 and features.iloc[1, 0] == 2.0 and np.isnan(features.iloc[2, 0])  # c は表に無い
    empty = FinishPowerFeatures().build(_records(pd.DataFrame()))
    assert empty.isna().all().all() and list(empty.columns) == list(FINISH_POWER_NAMES)
