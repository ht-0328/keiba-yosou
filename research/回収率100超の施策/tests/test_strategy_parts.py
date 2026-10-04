"""研究「回収率100超の施策」の部品（勝ち切る材料の表・3連単の出発点・作り方）のテスト。値は架空。
勝ち切る材料を読む部品は予想のパッケージに移したので、そちらのテスト（``src/yosou/shared/tests/test_finish_power.py``）で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, WIN, BaselineLogit, TrainingData
from yosou.shared.feature import BASE_FEATURES, FeatureCatalog, PredictionTiming
from yosou.shared.feature.odds import WIN_RATE

from 回収率100超の施策.analysis import (
    FINISH_NAMES,
    FINISH_TABLES,
    FINISH_VARIANTS,
    POOL_VARIANT,
    FinishTableBuilder,
    TrifectaWinBaseline,
    finish_table_named,
    spec_keyed,
)
from 回収率100超の施策.analysis.finish_columns import HORSE_NAMES, PEOPLE_NAMES
from 回収率100超の施策.analysis.trifecta_win_baseline import TRIFECTA_RATIO


def _training_data() -> TrainingData:
    ids = pd.DataFrame({RACE_ID: ["r0", "r0", "r1"], RACE_DATE: pd.Timestamp("2024-04-13"), HORSE_ID: ["a", "b", "a"], HORSE_NO: [1, 2, 1]})
    catalog = FeatureCatalog(BASE_FEATURES[:1])
    features = pd.DataFrame({catalog.names[0]: [1.0, 2.0, 3.0]})
    return TrainingData(ids, features, pd.DataFrame({WIN: [1, 0, 0]}), pd.DataFrame(index=ids.index), catalog, WIN)


def test_勝ち切る材料を元の表に足して一覧も広げる() -> None:
    base = _training_data()
    horses = pd.DataFrame({"race_id": ["r0", "r0"], "horse_id": ["a", "b"], **{name: [1.0, 0.0] for name in HORSE_NAMES}})
    people = pd.DataFrame({"race_id": ["r0"], "horse_id": ["a"], **{name: [0.6] for name in PEOPLE_NAMES}})
    records = horses.merge(people, on=["race_id", "horse_id"], how="outer")
    built = FinishTableBuilder().build(base, records)
    assert list(built.features.columns) == [base.catalog.names[0], *FINISH_NAMES]
    assert built.catalog.names == base.catalog.names + FINISH_NAMES and built.features.index.equals(base.features.index)
    assert built.features.loc[0, HORSE_NAMES[0]] == 1.0 and built.features.loc[0, PEOPLE_NAMES[0]] == 0.6
    assert np.isnan(built.features.loc[1, PEOPLE_NAMES[0]]) and np.isnan(built.features.loc[2, HORSE_NAMES[0]])  # 表に無い出走は欠損値
    assert built.targets is base.targets and built.label_name == WIN
    # もう同じ列があれば置き換える
    again = FinishTableBuilder().build(built, records)
    assert list(again.features.columns) == list(built.features.columns) and again.catalog.names == built.catalog.names


def test_表と作り方は前日と当日の2つで今の1着のモデルと比べる() -> None:
    assert [table.timing for table in FINISH_TABLES] == [PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY]
    day_before = finish_table_named("finish_ability")
    assert day_before.base == "h2h_ability" and set(FINISH_NAMES) <= set(day_before.catalog.names)
    spec = spec_keyed("finish-win-day_before")
    assert spec.current_table == "h2h_ability" and spec.current_key == "win-day_before" and spec.variant.uses_baseline
    assert set(FINISH_NAMES) <= set(spec.variant.columns) and "単勝オッズ" in spec.variant.columns and "対戦レーティング" in spec.variant.columns
    race_day = spec_keyed("finish-win-race_day")
    assert race_day.table.name == "finish_pool_ability" and TRIFECTA_RATIO in race_day.variant.columns
    assert set(race_day.variant.columns) <= set(race_day.table.catalog.names) and set(spec.variant.columns) <= set(spec.table.catalog.names)
    combined = spec_keyed("finish-pool-win-race_day")
    assert combined.pool_baseline and combined.table.name == "finish_pool_ability" and combined.current_key == "win-race_day"
    assert not race_day.pool_baseline and not spec.pool_baseline
    top3 = spec_keyed("finish-top3-race_day")
    assert top3.label == "3着以内" and top3.current_key == "h2h-race_day" and combined.label == "1着" and spec.label == "1着"
    assert len(FINISH_VARIANTS) == 4
    with pytest.raises(ValueError):
        spec_keyed("finish-win-thursday")
    with pytest.raises(ValueError):
        finish_table_named("finish_thursday")


def test_出発点を3連単から見た勝率に替え3連単の無い馬は元のまま() -> None:
    ids = pd.DataFrame({RACE_ID: ["r0"] * 3, RACE_DATE: pd.Timestamp("2024-04-13"), HORSE_ID: ["a", "b", "c"], HORSE_NO: [1, 2, 3]})
    market = pd.Series([0.5, 0.3, 0.2])
    features = pd.DataFrame({TRIFECTA_RATIO: [np.log(1.2), np.log(0.5), np.nan]})
    baseline = BaselineLogit(np.log(market / (1 - market)), PredictionTiming.DAY_BEFORE)
    data = TrainingData(ids, features, pd.DataFrame({WIN: [1, 0, 0]}), pd.DataFrame({WIN_RATE: market}), FeatureCatalog(()), WIN, baseline=baseline)
    pooled = TrifectaWinBaseline().apply(data)
    probabilities = pooled.baseline.probabilities()
    assert probabilities.iloc[0] == pytest.approx(0.6) and probabilities.iloc[1] == pytest.approx(0.15)
    assert probabilities.iloc[2] == pytest.approx(0.2)  # 3連単の比が無ければ元の基準
    assert pooled.baseline.known_from is PredictionTiming.RACE_DAY and pooled.features is data.features
    assert POOL_VARIANT.key == "win-pool-race_day" and POOL_VARIANT.uses_baseline and TRIFECTA_RATIO in POOL_VARIANT.columns
    with pytest.raises(ValueError):
        TrifectaWinBaseline().apply(TrainingData(ids, features, data.targets, data.evaluation, FeatureCatalog(()), WIN))
