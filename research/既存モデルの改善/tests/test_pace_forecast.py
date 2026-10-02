"""展開の予想の結果（P）を足す確かめの部品（予測の読み方・表の足し方・作り方）。合成データだけを使う。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.race_development.feature import GroupForecast
from yosou.race_development.repository import OutOfSampleRepository
from yosou.race_development.workflow import PaceForecastHistory
from yosou.shared.dataset import HORSE_ID, RACE_DATE, RACE_ID, TOP3, TrainingData
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming
from yosou.shared.feature.pace_forecast import PACE_FORECAST_NAMES, SOURCE_COLUMNS
from yosou.shared.feature.pace_forecast import pace_forecast_columns as names

from 既存モデルの改善.analysis.pace_forecast import (
    PACE_COMPARISONS,
    PACE_NAMES,
    PACE_TABLES,
    PaceTableBuilder,
    pace_table_named,
)

_TIMING = PredictionTiming.RACE_DAY


def _save(root: Path, group: str, year: int, horses: dict, races: dict) -> None:
    OutOfSampleRepository(root / "out_of_sample").save(group, _TIMING, year, "テスト", GroupForecast(pd.DataFrame(horses),
                                                                                                    pd.DataFrame(races)))


@pytest.fixture()
def development_root(tmp_path: Path) -> Path:
    """前半は 2つの年、後半は後の年だけの予測（後半は前半より1年遅く始まる）。"""
    for year, race in ((2016, "r16"), (2017, "r17")):
        _save(tmp_path, "early", year,
              {RACE_ID: [race, race], HORSE_ID: ["a", "b"], "p_leader": [0.7, 0.3], "p_front": [0.9, 0.4],
               "p_middle": [0.08, 0.4], "p_back": [0.02, 0.2]},
              {RACE_ID: [race], "p_slow": [0.3], "p_even": [0.4], "p_high": [0.3],
               "first_q10": [-1.0], "first_q50": [0.1], "first_q90": [1.0]})
    _save(tmp_path, "late", 2017, {RACE_ID: ["r17", "r17"], HORSE_ID: ["a", "b"], "corner4_pred": [0.1, 0.6],
                                   "closing_pred": [0.5, 0.3]},
          {RACE_ID: ["r17"], "second_q10": [-0.8], "second_q50": [0.2], "second_q90": [1.1]})
    return tmp_path


def test_reader_joins_early_and_late_forecasts_of_every_year(development_root: Path):
    reader = PaceForecastHistory(development_root)
    table = reader.read(_TIMING)
    assert list(table.columns) == [*names.KEY, *SOURCE_COLUMNS] and len(table) == 4
    assert reader.years(_TIMING) == {"early": [2016, 2017], "late": [2017]}
    by_key = table.set_index(names.KEY)
    # レースごとの予測は同じレースの馬に配る。後半の予測が無い年（2016年）の馬は、後半の列が欠損値
    assert by_key.loc[("r16", "b"), names.HIGH] == pytest.approx(0.3)
    assert np.isnan(by_key.loc[("r16", "a"), names.CORNER4])
    assert by_key.loc[("r17", "b"), names.CORNER4] == pytest.approx(0.6)
    assert by_key.loc[("r17", "a"), names.SECOND_MIDDLE] == pytest.approx(0.2)


def test_reader_asks_for_the_backtest_when_nothing_is_stored(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="backtest"):
        PaceForecastHistory(tmp_path).read(_TIMING)


def test_builder_adds_the_twenty_columns_to_the_same_runs(development_root: Path):
    catalog = FeatureCatalog((Feature("x", "A", FeatureKind.NUMERIC),))
    ids = pd.DataFrame({RACE_ID: ["r17", "r16", "r15"], HORSE_ID: ["a", "b", "a"],
                        RACE_DATE: pd.to_datetime(["2017-05-01", "2016-05-01", "2015-05-01"])})
    base = TrainingData(ids, pd.DataFrame({"x": [1.0, 2.0, 3.0]}), pd.DataFrame({TOP3: [1, 0, 0]}),
                        pd.DataFrame(index=ids.index), catalog, TOP3)
    paced_catalog = FeatureCatalog(catalog.features + tuple(Feature(name, "P", FeatureKind.NUMERIC) for name in PACE_FORECAST_NAMES))
    paced = PaceTableBuilder().build(base, PaceForecastHistory(development_root).read(_TIMING), paced_catalog)
    assert list(paced.features.columns) == ["x", *PACE_FORECAST_NAMES]
    assert paced.features["x"].tolist() == [1.0, 2.0, 3.0] and paced.targets.equals(base.targets)
    assert paced.features.loc[0, names.CORNER4_P] == pytest.approx(0.1) and paced.features.loc[0, names.CORNER4_RANK] == 1
    # 予測の無い年（2015年）の行は欠損値
    assert paced.features.loc[2, list(PACE_FORECAST_NAMES)].isna().all()


def test_each_timing_compares_the_current_columns_with_and_without_p():
    assert [spec.timing for spec in PACE_COMPARISONS] == list(PredictionTiming)
    expected = {PredictionTiming.THURSDAY: ABILITY_CATALOG, PredictionTiming.DAY_BEFORE: ABILITY_CATALOG,
                PredictionTiming.RACE_DAY: RACE_DAY_CATALOG}
    for spec in PACE_COMPARISONS:
        assert spec.current.columns == expected[spec.timing].columns_for(spec.timing)
        assert spec.paced.columns == spec.current.columns + PACE_NAMES
        assert spec.paced.uses_baseline == spec.current.uses_baseline == (spec.timing is not PredictionTiming.THURSDAY)
        table = pace_table_named(spec.paced.model)
        assert table.timing is spec.timing and set(spec.paced.columns) <= set(table.catalog.names)
    assert len(PACE_TABLES) == 3
