"""材料を差し替えて確かめる部品（入口⑭ ``material_check.py``）。手で作った表だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.ability_score import ABILITY_INDEX, ABILITY_SCORE_NAMES, CARRIED
from yosou.development_score import DEVELOPMENT_SCORE_NAMES
from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3, WIN, TrainingData
from yosou.shared.feature import BASE_FEATURES, FINISH_POWER_NAMES, FeatureCatalog, PredictionTiming

from 既存モデルの改善.analysis.material_check import (
    CURRENT_PRODUCTION,
    PAYBACK_RESEARCH,
    AbilityScoreTableBuilder,
    comparison_keyed,
    current_production,
    material_comparisons,
    material_named,
    material_table_named,
    material_tables,
)
from 既存モデルの改善.analysis.pace_forecast import PACE_NAMES


def _training_data() -> TrainingData:
    ids = pd.DataFrame({RACE_ID: ["r0", "r0", "r1"], RACE_DATE: pd.Timestamp("2024-04-13"), HORSE_ID: ["a", "b", "a"], HORSE_NO: [1, 2, 1]})
    catalog = FeatureCatalog(BASE_FEATURES[:1])
    features = pd.DataFrame({catalog.names[0]: [1.0, 2.0, 3.0], ABILITY_INDEX: [80.0, 78.0, np.nan], CARRIED: [57.0, 55.0, 55.0]})
    return TrainingData(ids, features, pd.DataFrame({TOP3: [1, 0, 0]}), pd.DataFrame(index=ids.index), catalog, TOP3)


def test_the_ability_score_builder_adds_the_four_columns_from_the_table_itself() -> None:
    base = _training_data()
    builder = AbilityScoreTableBuilder()
    builder.prepare(None)   # 元DB は要らない
    built = builder.build(base, PredictionTiming.DAY_BEFORE)
    assert list(built.features.columns) == [base.catalog.names[0], ABILITY_INDEX, CARRIED, *ABILITY_SCORE_NAMES]
    assert built.catalog.names == base.catalog.names + ABILITY_SCORE_NAMES and built.features.index.equals(base.features.index)
    assert built.features.loc[0, ABILITY_SCORE_NAMES[0]] == 79.0 and np.isnan(built.features.loc[2, ABILITY_SCORE_NAMES[0]])
    assert built.targets is base.targets


def test_the_current_production_covers_the_six_models_and_the_day_before_top3_includes_s() -> None:
    assert len(CURRENT_PRODUCTION) == 6
    assert {(current.timing, current.label) for current in CURRENT_PRODUCTION} == {(t, l) for t in PredictionTiming for l in (TOP3, WIN)}
    day_before = current_production(PredictionTiming.DAY_BEFORE, TOP3)
    assert set(DEVELOPMENT_SCORE_NAMES) <= set(day_before.columns) and day_before.key == "dscore-day_before"
    assert not set(DEVELOPMENT_SCORE_NAMES) & set(current_production(PredictionTiming.DAY_BEFORE, WIN).columns)
    race_day_win = current_production(PredictionTiming.RACE_DAY, WIN)
    assert race_day_win.research == PAYBACK_RESEARCH and set(FINISH_POWER_NAMES) <= set(race_day_win.columns)
    assert set(PACE_NAMES) <= set(current_production(PredictionTiming.THURSDAY, TOP3).columns)
    assert not current_production(PredictionTiming.THURSDAY, WIN).uses_baseline


def test_each_comparison_is_the_current_model_plus_the_material() -> None:
    material = material_named("能力スコア")
    assert len(material_tables(material)) == 4 and len(material_comparisons(material)) == 6
    for spec in material_comparisons(material):
        assert set(material.names) <= set(spec.added.columns) <= set(spec.table.catalog.names)
        assert set(spec.current.columns) <= set(spec.added.columns) and spec.added.uses_baseline == spec.current.uses_baseline
        assert spec.added.timing is spec.current.timing and spec.table.base == spec.current.base_table
    assert comparison_keyed(material, "ascore-day_before").table.name == "ascore_day_before"
    assert comparison_keyed(material, "ascore-win-race_day").table.name == "ascore_finish_race_day"
    assert material_table_named(material, "ascore_thursday").base == "dscore_thursday"
    with pytest.raises(ValueError):
        comparison_keyed(material, "ascore-sunday")
    with pytest.raises(ValueError):
        material_named("知らない材料")
