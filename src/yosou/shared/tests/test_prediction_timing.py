"""どの予想でも使う特徴量の一覧（設計書 09）と、時点ごとに使う特徴量（設計書 07）が設計書どおりであることを固定する。"""

from __future__ import annotations

from collections import Counter

import pytest

from ..feature import BASE_FEATURES, Feature, FeatureCatalog, FeatureKind, PredictionTiming
from ..ml_model.lightgbm_encoder import RARE_GROUPED_COLUMNS

CATALOG = FeatureCatalog(BASE_FEATURES)


def test_catalog_has_71_features_in_design_groups():
    assert len(BASE_FEATURES) == 71 and len(set(CATALOG.names)) == 71
    assert Counter(feature.group for feature in BASE_FEATURES) == {
        "A": 9, "B": 9, "C": 6, "D": 11, "E": 10, "F": 10, "G": 4, "H": 6, "I": 6,
    }


def test_catalog_rejects_a_repeated_name():
    twice = (Feature("斤量", "B", FeatureKind.NUMERIC), Feature("斤量", "B", FeatureKind.NUMERIC))
    with pytest.raises(ValueError, match="重なって"):
        FeatureCatalog(twice)


def test_rare_grouped_columns_are_categorical_features():
    assert set(RARE_GROUPED_COLUMNS) <= CATALOG.categorical


@pytest.mark.parametrize(("timing", "count"), [
    (PredictionTiming.THURSDAY, 62), (PredictionTiming.DAY_BEFORE, 69), (PredictionTiming.RACE_DAY, 71),
])
def test_feature_count_per_timing(timing: PredictionTiming, count: int):
    assert len(CATALOG.columns_for(timing)) == count


def test_thursday_and_day_before_drop_what_is_not_known_yet():
    thursday = set(CATALOG.columns_for(PredictionTiming.THURSDAY))
    day_before = set(CATALOG.columns_for(PredictionTiming.DAY_BEFORE))
    assert set(CATALOG.names) - day_before == {"馬体重", "馬体重の増減"}
    assert set(CATALOG.names) - thursday == {
        "枠番", "馬番", "馬体重", "馬体重の増減", "馬場状態",
        "同じ芝ダ・馬場状態での通算の出走数", "同じ芝ダ・馬場状態での通算の3着以内の数",
        "持ち時計のレース内順位（コース単位）", "持ち時計のレース内順位（距離単位）",
    }


def test_feature_columns_keep_catalog_order():
    columns = CATALOG.columns_for(PredictionTiming.THURSDAY)
    assert list(columns) == [name for name in CATALOG.names if name in columns]


@pytest.mark.parametrize("text", ["当日", "race_day", " 当日 "])
def test_parse_accepts_label_and_value(text: str):
    assert PredictionTiming.parse(text) is PredictionTiming.RACE_DAY


def test_parse_rejects_unknown_timing():
    with pytest.raises(ValueError, match="知らない時点"):
        PredictionTiming.parse("発走直前")


def test_a_feature_known_from_day_before_is_not_used_on_thursday():
    # 予想ごとに足す特徴量は、いつから分かるかを Feature に書く（例: オッズは前日から）
    odds = Feature("単勝オッズ", "J", FeatureKind.NUMERIC, PredictionTiming.DAY_BEFORE)
    catalog = FeatureCatalog(BASE_FEATURES + (odds,))
    assert "単勝オッズ" not in catalog.columns_for(PredictionTiming.THURSDAY)
    assert catalog.columns_for(PredictionTiming.DAY_BEFORE)[-1] == "単勝オッズ"
    assert len(catalog.columns_for(PredictionTiming.RACE_DAY)) == 72


def test_timings_are_ordered_thursday_day_before_race_day():
    assert PredictionTiming.RACE_DAY.is_at_or_after(PredictionTiming.DAY_BEFORE)
    assert PredictionTiming.DAY_BEFORE.is_at_or_after(PredictionTiming.DAY_BEFORE)
    assert not PredictionTiming.THURSDAY.is_at_or_after(PredictionTiming.DAY_BEFORE)
