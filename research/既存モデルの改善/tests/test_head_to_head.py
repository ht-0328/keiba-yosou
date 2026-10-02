"""対戦レーティングを足した比べの部品。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TOP3, TrainingData
from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.feature import BASE_FEATURES, HEAD_TO_HEAD_FEATURES, FeatureCatalog, PredictionTiming

from 既存モデルの改善.analysis.head_to_head import (
    BASE_TABLES,
    H2H_COMPARISONS,
    H2H_NAMES,
    H2H_VARIANTS,
    SCORE,
    RatedTableBuilder,
    TimingComparison,
    base_table_rated,
)
from 既存モデルの改善.analysis.walk_forward import WINDOW

_RNG = np.random.default_rng(0)


def _training_data(rows: int = 12) -> TrainingData:
    """3頭立て × 4レースの、特徴量1個だけの学習データ。"""
    ids = pd.DataFrame({RACE_ID: [f"r{index // 3}" for index in range(rows)], RACE_DATE: pd.Timestamp("2024-01-06"),
                        HORSE_ID: [f"h{index % 5}" for index in range(rows)], HORSE_NO: [index % 3 + 1 for index in range(rows)]})
    catalog = FeatureCatalog(BASE_FEATURES[:1])
    features = pd.DataFrame({catalog.names[0]: np.arange(rows, dtype=float)})
    return TrainingData(ids, features, pd.DataFrame({TOP3: [1, 0, 0] * (rows // 3)}), pd.DataFrame(index=ids.index), catalog, TOP3)


def test_rated_table_adds_the_seven_columns_and_widens_the_catalog():
    base = _training_data()
    runs = pd.DataFrame({"race_id": ["r0"] * 3 + ["r1"] * 3, "race_date": pd.to_datetime(["2024-01-05"] * 3 + ["2024-01-06"] * 3),
                         "horse_id": ["h0", "h1", "h2", "h3", "h4", "h0"], "finish": [1, 2, 3, 1, 2, 3], "is_target": True})
    rated = RatedTableBuilder().build(base, runs)
    assert list(rated.features.columns) == list(base.features.columns) + list(H2H_NAMES)
    assert rated.catalog.features == base.catalog.features + HEAD_TO_HEAD_FEATURES
    assert rated.features.index.equals(base.features.index) and rated.ids is base.ids
    # 記録の無い出走（r2・r3）は欠損値、記録のある r1 の馬には値が入る
    assert rated.features.loc[3:5, H2H_NAMES[0]].notna().all() and rated.features.loc[6:, H2H_NAMES[0]].isna().all()


def test_rated_table_replaces_rating_columns_the_base_already_has():
    # O を採用したあとの組み立て関数で作った元の表には、もう O の列がある。重ねて足さず、作り直した値で置き換える
    plain = _training_data()
    stale = pd.DataFrame({name: -1.0 for name in H2H_NAMES}, index=plain.features.index)
    base = TrainingData(plain.ids, pd.concat([plain.features, stale], axis=1), plain.targets, plain.evaluation,
                        FeatureCatalog(plain.catalog.features + HEAD_TO_HEAD_FEATURES), TOP3)
    runs = pd.DataFrame({"race_id": ["r0"] * 3, "race_date": pd.to_datetime(["2024-01-05"] * 3),
                         "horse_id": ["h0", "h1", "h2"], "finish": [1, 2, 3], "is_target": True})
    rated = RatedTableBuilder().build(base, runs)
    assert list(rated.features.columns) == list(plain.features.columns) + list(H2H_NAMES)
    assert rated.catalog.names == plain.catalog.names + H2H_NAMES and not (rated.features[list(H2H_NAMES)] == -1.0).any().any()


def test_base_tables_read_without_the_rating_and_the_rated_catalog_adds_it_once():
    # 本番の木曜・前日の一覧には O が入っているので、元の表の一覧からは除き、対戦レーティングを足した一覧に1回だけ足す
    for table in BASE_TABLES:
        assert not set(H2H_NAMES) & set(table.catalog.names)
        assert table.rated_catalog.names == table.catalog.names + H2H_NAMES


def test_variants_pair_the_current_columns_with_the_rated_ones_per_timing():
    assert [spec.timing for spec in H2H_COMPARISONS] == list(PredictionTiming)
    for spec in H2H_COMPARISONS:
        assert spec.rated.columns == spec.current.columns + H2H_NAMES
        assert not set(H2H_NAMES) & set(spec.current.columns)
        assert spec.current.uses_baseline == spec.rated.uses_baseline == (spec.timing is not PredictionTiming.THURSDAY)
        assert spec.current.model == spec.rated.model == base_table_rated(spec.current.model).rated_name
    assert len(H2H_VARIANTS) == 6 and len({variant.key for variant in H2H_VARIANTS}) == 6
    assert {table.rated_name for table in BASE_TABLES} == {variant.model for variant in H2H_VARIANTS}


def _predictions(scores: list[float], windows: list[str]) -> pd.DataFrame:
    rows = len(scores)
    return pd.DataFrame({RACE_ID: [f"r{index // 2}" for index in range(rows)], HORSE_ID: [f"h{index}" for index in range(rows)],
                         HORSE_NO: [index % 2 + 1 for index in range(rows)], POPULARITY: [index % 2 + 1 for index in range(rows)],
                         TOP3: [1, 0] * (rows // 2), SCORE: scores, WINDOW: windows})


def test_timing_comparison_adopts_when_five_windows_and_the_whole_period_are_better():
    windows = [name for name in ("w1", "w2", "w3", "w4", "w5", "w6", "w7") for _ in range(2)]
    current = _predictions([0.6, 0.4] * 7, windows)
    # 6つの区切りで良く（当たりに高い確率）、1つの区切り（w7）だけ悪い
    better = [0.7, 0.3] * 6 + [0.5, 0.5]
    rated = _predictions(better, windows)
    comparison = TimingComparison()
    table = comparison.by_window(*comparison.common(current, rated))
    assert table[WINDOW].tolist() == ["w1", "w2", "w3", "w4", "w5", "w6", "w7", "全期間"]
    assert table["小さい"].tolist() == [True] * 6 + [False, True] and comparison.adopted(table)
    # 7つのうち 4つしか良くなければ満たさない
    worse = _predictions([0.7, 0.3] * 4 + [0.5, 0.5] * 3, windows)
    assert not comparison.adopted(comparison.by_window(*comparison.common(current, worse)))


def test_timing_comparison_keeps_only_the_rows_in_both():
    current = _predictions([0.6, 0.4, 0.6, 0.4], ["w1"] * 4)
    rated = _predictions([0.7, 0.3], ["w1"] * 2)
    both_current, both_rated = TimingComparison().common(current, rated)
    assert len(both_current) == len(both_rated) == 2 and both_current[HORSE_ID].tolist() == both_rated[HORSE_ID].tolist()
