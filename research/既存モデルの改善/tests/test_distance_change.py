"""距離の変更の傾向（まとまり R）を足した比べの部品（入口⑫ ``distance_check.py``）。手で作った表だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3, WIN, TrainingData
from yosou.shared.feature import BASE_FEATURES, FINISH_POWER_NAMES, FeatureCatalog, PredictionTiming
from yosou.shared.feature.history import DISTANCE_CHANGE_NAMES

from 既存モデルの改善.analysis.distance_change import (
    DISTANCE_TABLES,
    DISTANCE_VARIANTS,
    PAYBACK_RESEARCH,
    DistanceTableBuilder,
    distance_table_named,
    spec_keyed,
)
from 既存モデルの改善.analysis.pace_forecast import PACE_NAMES


def _training_data() -> TrainingData:
    ids = pd.DataFrame({RACE_ID: ["r0", "r0", "r1"], RACE_DATE: pd.Timestamp("2024-04-13"), HORSE_ID: ["a", "b", "a"], HORSE_NO: [1, 2, 1]})
    catalog = FeatureCatalog(BASE_FEATURES[:1])
    features = pd.DataFrame({catalog.names[0]: [1.0, 2.0, 3.0]})
    return TrainingData(ids, features, pd.DataFrame({TOP3: [1, 0, 0]}), pd.DataFrame(index=ids.index), catalog, TOP3)


def test_the_builder_adds_the_seven_columns_by_race_and_horse_and_replaces_them_when_built_again() -> None:
    base = _training_data()
    records = pd.DataFrame({"race_id": ["r0", "r1"], "horse_id": ["b", "a"], **{name: [2.0, 3.0] for name in DISTANCE_CHANGE_NAMES}})
    built = DistanceTableBuilder().build(base, records)
    assert list(built.features.columns) == [base.catalog.names[0], *DISTANCE_CHANGE_NAMES]
    assert built.catalog.names == base.catalog.names + DISTANCE_CHANGE_NAMES and built.features.index.equals(base.features.index)
    first = DISTANCE_CHANGE_NAMES[0]
    assert np.isnan(built.features.loc[0, first]) and built.features.loc[1, first] == 2.0 and built.features.loc[2, first] == 3.0
    assert built.targets is base.targets
    again = DistanceTableBuilder().build(built, records)
    assert list(again.features.columns) == list(built.features.columns) and again.catalog.names == built.catalog.names


def test_each_variant_is_the_current_model_of_its_timing_and_target_plus_r() -> None:
    assert len(DISTANCE_TABLES) == 4 and len(DISTANCE_VARIANTS) == 6
    for spec in DISTANCE_VARIANTS:
        assert set(DISTANCE_CHANGE_NAMES) <= set(spec.variant.columns) <= set(spec.table.catalog.names)
        assert spec.variant.uses_baseline == (spec.timing is not PredictionTiming.THURSDAY)
    thursday = spec_keyed("dist-thursday")
    assert thursday.current_table == "pace_thursday" and thursday.current_key == "pace-thursday" and thursday.label == TOP3
    assert set(PACE_NAMES) <= set(thursday.variant.columns)
    day_before_win = spec_keyed("dist-win-day_before")
    assert day_before_win.current_table == "h2h_ability" and day_before_win.current_key == "win-day_before" and day_before_win.label == WIN
    race_day = spec_keyed("dist-race_day")
    assert race_day.current_key == "current-race_day" and not set(FINISH_POWER_NAMES) & set(race_day.variant.columns)
    race_day_win = spec_keyed("dist-win-race_day")
    assert race_day_win.current_research == PAYBACK_RESEARCH and race_day_win.current_table == "finish_pool_ability"
    assert race_day_win.current_key == "finish-win-race_day" and set(FINISH_POWER_NAMES) <= set(race_day_win.variant.columns)
    assert distance_table_named("dist_finish_pool_ability").base_research == PAYBACK_RESEARCH
    with pytest.raises(ValueError):
        spec_keyed("dist-friday")
    with pytest.raises(ValueError):
        distance_table_named("dist_friday")
