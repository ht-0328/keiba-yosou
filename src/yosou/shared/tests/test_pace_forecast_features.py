"""まとまり P（展開の予想の結果）の作り方。DB を使わず、手で作った予測の表を渡して確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ..feature import PACE_FORECAST_FEATURES, EntryRecords, PredictionTiming, WorkoutCoverage
from ..feature.group import PaceForecastFeatures
from ..feature.pace_forecast import PACE_FORECAST_NAMES, SOURCE_COLUMNS, PaceForecastTableBuilder
from ..feature.pace_forecast import pace_forecast_columns as names


def _forecasts() -> pd.DataFrame:
    """2レース（r1 は3頭、r2 は1頭）の展開の予測。レースごとの列は同じレースの馬に同じ値。"""
    return pd.DataFrame({
        "race_id": ["r1", "r1", "r1", "r2"], "horse_id": ["a", "b", "c", "d"],
        names.LEADER: [0.6, 0.3, 0.1, 1.0], names.FRONT: [0.8, 0.5, 0.2, 0.9],
        names.MIDDLE: [0.15, 0.3, 0.3, 0.05], names.BACK: [0.05, 0.2, 0.5, 0.05],
        names.SLOW: [0.2, 0.2, 0.2, 0.5], names.HIGH: [0.4, 0.4, 0.4, 0.1],
        names.FIRST_LOW: [-1.0] * 3 + [-0.5], names.FIRST_MIDDLE: [0.0] * 3 + [0.2], names.FIRST_HIGH: [1.5] * 3 + [0.9],
        names.CORNER4: [0.1, 0.5, 0.9, 0.3], names.CLOSING: [0.6, 0.2, 0.4, 0.5], names.SECOND_MIDDLE: [0.3] * 3 + [-0.1],
    })


def test_the_twenty_features_are_numbers_in_group_p_known_from_thursday():
    assert [feature.name for feature in PACE_FORECAST_FEATURES] == list(PACE_FORECAST_NAMES)
    assert len(PACE_FORECAST_NAMES) == 20 and len(SOURCE_COLUMNS) == 12
    assert all(feature.group == "P" and feature.is_known_at(PredictionTiming.THURSDAY) for feature in PACE_FORECAST_FEATURES)


def test_forecasts_become_ranks_and_spreads_within_the_race():
    ids = pd.Series(["r1", "r1", "r1", "r2"], index=[10, 11, 12, 13]), pd.Series(["c", "a", "b", "d"], index=[10, 11, 12, 13])
    table = PaceForecastTableBuilder().build(*ids, _forecasts())
    assert list(table.columns) == list(PACE_FORECAST_NAMES) and list(table.index) == [10, 11, 12, 13]
    row_a = table.loc[11]
    # 先頭の確率は高い順、4コーナーの位置と上がりは小さい順（前・速い順）に順位を付ける
    assert row_a[names.LEADER_RANK] == 1 and row_a[names.LEADER_GAP] == 0 and row_a[names.CORNER4_RANK] == 1
    assert table.loc[10, names.LEADER_GAP] == pytest.approx(-0.5)
    assert table.loc[12, names.CLOSING_RANK] == 1 and table.loc[11, names.COMBINED] == pytest.approx(0.7)
    # 偏差は (0.1 − 0.5) ÷ 0.4。1頭立てのレースは欠損値
    assert row_a[names.CORNER4_Z] == pytest.approx(-1.0)
    assert np.isnan(table.loc[13, names.CORNER4_Z])
    assert row_a[names.FIRST_WIDTH] == pytest.approx(2.5) and table.loc[13, names.SECOND_DIFF] == pytest.approx(-0.1)


def test_runs_without_a_forecast_are_missing():
    table = PaceForecastTableBuilder().build(pd.Series(["r1", "r9"]), pd.Series(["a", "z"]), _forecasts())
    assert table.iloc[0].notna().all() and table.iloc[1].isna().all()


def test_the_group_reads_the_forecasts_in_the_records():
    entries = pd.DataFrame({"race_id": ["r1", "r1"], "horse_id": ["b", "a"]})
    empty = pd.DataFrame()
    records = EntryRecords(entries=entries, past_runs=empty, workouts=empty, workout_coverage=WorkoutCoverage.complete(),
                           jockey_days=empty, trainer_days=empty, sire_days=empty, damsire_days=empty,
                           pace_forecasts=_forecasts())
    features = PaceForecastFeatures().build(records)
    assert features[names.LEADER_P].tolist() == [0.3, 0.6]
    # 予測を入れていない予想では、全部欠損値
    missing = PaceForecastFeatures().build(EntryRecords(entries=entries, past_runs=empty, workouts=empty,
                                                        workout_coverage=WorkoutCoverage.complete(), jockey_days=empty,
                                                        trainer_days=empty, sire_days=empty, damsire_days=empty))
    assert missing.isna().all().all() and list(missing.columns) == list(PACE_FORECAST_NAMES)
