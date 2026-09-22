"""特徴量の一覧（設計書 09）と、時点ごとに使う特徴量（設計書 07）が設計書どおりであることを固定する。"""

from __future__ import annotations

from collections import Counter

import pytest

from ..feature import CATEGORICAL_FEATURES, FEATURE_NAMES, FEATURES, PredictionTiming
from ..ml_model.lightgbm_encoder import RARE_GROUPED_COLUMNS


def test_catalog_has_71_features_in_design_groups():
    assert len(FEATURES) == 71 and len(set(FEATURE_NAMES)) == 71
    assert Counter(feature.group for feature in FEATURES) == {
        "A": 9, "B": 9, "C": 6, "D": 11, "E": 10, "F": 10, "G": 4, "H": 6, "I": 6,
    }


def test_rare_grouped_columns_are_categorical_features():
    assert set(RARE_GROUPED_COLUMNS) <= CATEGORICAL_FEATURES


@pytest.mark.parametrize(("timing", "count"), [
    (PredictionTiming.THURSDAY, 62), (PredictionTiming.DAY_BEFORE, 69), (PredictionTiming.RACE_DAY, 71),
])
def test_feature_count_per_timing(timing: PredictionTiming, count: int):
    assert len(timing.feature_columns()) == count


def test_thursday_and_day_before_drop_what_is_not_known_yet():
    thursday = set(PredictionTiming.THURSDAY.feature_columns())
    day_before = set(PredictionTiming.DAY_BEFORE.feature_columns())
    assert set(FEATURE_NAMES) - day_before == {"馬体重", "馬体重の増減"}
    assert set(FEATURE_NAMES) - thursday == {
        "枠番", "馬番", "馬体重", "馬体重の増減", "馬場状態",
        "同じ芝ダ・馬場状態での通算の出走数", "同じ芝ダ・馬場状態での通算の3着以内の数",
        "持ち時計のレース内順位（コース単位）", "持ち時計のレース内順位（距離単位）",
    }


def test_feature_columns_keep_catalog_order():
    columns = PredictionTiming.THURSDAY.feature_columns()
    assert list(columns) == [name for name in FEATURE_NAMES if name in columns]


@pytest.mark.parametrize("text", ["当日", "race_day", " 当日 "])
def test_parse_accepts_label_and_value(text: str):
    assert PredictionTiming.parse(text) is PredictionTiming.RACE_DAY


def test_parse_rejects_unknown_timing():
    with pytest.raises(ValueError, match="知らない時点"):
        PredictionTiming.parse("発走直前")
