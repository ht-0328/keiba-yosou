"""近さのモデル（特徴量の変換・グループごとの近さ）と、単位の決め方。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind

from ..similarity import FeatureMatrix, GroupSimilarity
from ..unit import CourseUnitMap

_CATALOG = FeatureCatalog((
    Feature("距離", "A", FeatureKind.NUMERIC), Feature("馬場状態", "A", FeatureKind.CATEGORICAL),
    Feature("騎手", "C", FeatureKind.CATEGORICAL), Feature("馬体重", "B", FeatureKind.NUMERIC),
    Feature("単勝オッズ", "K", FeatureKind.NUMERIC),
))


def _features() -> pd.DataFrame:
    return pd.DataFrame({
        "距離": [1600.0, 1600.0, 1600.0, 1600.0], "馬場状態": ["良", "重", "良", None],
        "騎手": ["甲", "乙", "丙", "丁"], "馬体重": [480.0, np.nan, 500.0, 460.0], "単勝オッズ": [1.5, 2.0, 2.5, 3.0],
    })


def test_feature_matrix_fills_scales_and_encodes():
    matrix = FeatureMatrix(_CATALOG, ["騎手"], {"K": 1.0}, add_missing_flags=True).fit(_features())
    # 距離はどの行も同じなので使わない。騎手は使わない特徴量。欠損値だったかの列と one-hot の列が足される
    assert matrix.column_names == ["馬体重", "単勝オッズ", "馬体重（欠損値）", "馬場状態=良", "馬場状態=重"]
    values = matrix.transform(_features())
    # 欠損値は中央値（480）で埋めてから標準化するので、平均と同じ値になる
    assert values[1, 0] == pytest.approx(0.0)
    assert values[1, 2] == pytest.approx(1 / np.sqrt(2))
    # 学習データに無い馬場状態（不良）と欠損値は、どの one-hot の列も 0
    unknown = _features().assign(馬場状態=["不良", None, "良", "良"])
    assert matrix.transform(unknown)[0, 3:].tolist() == [0.0, 0.0]


def test_feature_matrix_drops_groups_with_zero_weight():
    matrix = FeatureMatrix(_CATALOG, [], {"K": 0.0, "C": 0.0}, add_missing_flags=False).fit(_features())
    assert "単勝オッズ" not in matrix.column_names and not any(name.startswith("騎手") for name in matrix.column_names)
    assert "馬体重（欠損値）" not in matrix.column_names


def test_group_similarity_scores_members_higher_than_outsiders():
    rng = np.random.default_rng(0)
    group = rng.normal(0.0, 1.0, size=(40, 2))
    others = rng.normal(6.0, 1.0, size=(40, 2))
    matrix = np.vstack([group, others])
    is_member = np.array([True] * 40 + [False] * 40)
    similarity = GroupSimilarity(k=5).fit(matrix, is_member)
    scores = similarity.scores(np.array([[0.0, 0.0], [6.0, 6.0]]))
    # 点数は、単位の1番人気全員（グループの外の馬も含む）と比べた順位。グループの真ん中は高く、外の馬の真ん中は低い
    assert scores[0] > 80 and scores[1] < 50
    assert similarity.scores(matrix).min() >= 0 and similarity.scores(matrix).max() <= 100


def test_group_similarity_caps_k_and_needs_two_members():
    matrix = np.array([[0.0], [1.0], [5.0]])
    assert GroupSimilarity(k=10).fit(matrix, np.array([True, True, False])).k == 1
    with pytest.raises(ValueError, match="2頭以上"):
        GroupSimilarity(k=3).fit(matrix, np.array([True, False, False]))


def test_course_unit_map_merges_small_distances_into_the_nearest_unit():
    rows = pd.DataFrame({
        "芝ダ": ["芝"] * 9 + ["ダート"] * 3,
        "距離": [1600] * 3 + [2000] * 3 + [1800, 2400, 1700] + [1200, 1200, 1000],
    })
    unit_map = CourseUnitMap.from_rows(rows, min_rows=3)
    assert unit_map.distances == {"芝": (1600, 2000), "ダート": (1200,)}
    # 差が同じなら長いほう。2400 は 2000 にまとまる。ダートは 1200 だけが単位
    assert unit_map.unit_of("芝", 1800) == "芝2000m" and unit_map.unit_of("芝", 1700) == "芝1600m"
    assert unit_map.unit_of("芝", 2400) == "芝2000m" and unit_map.unit_of("ダート", 1000) == "ダート1200m"
    assert unit_map.members(rows) == {"ダート1200m": [1000, 1200], "芝1600m": [1600, 1700], "芝2000m": [1800, 2000, 2400]}
    with pytest.raises(ValueError, match="障害"):
        unit_map.unit_of("障害", 3000)


def test_course_unit_map_keeps_one_unit_when_every_distance_is_small():
    rows = pd.DataFrame({"芝ダ": ["芝"] * 3, "距離": [1200, 1400, 1400]})
    assert CourseUnitMap.from_rows(rows, min_rows=10).distances == {"芝": (1400,)}
