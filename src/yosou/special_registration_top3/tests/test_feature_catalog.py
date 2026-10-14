"""特徴量の一覧（設計書 09）。DB を使わない。"""

from __future__ import annotations

from yosou.ability_score import ABILITY_SCORE_NAMES
from yosou.shared.feature import ABILITY_FEATURES, HEAD_TO_HEAD_FEATURES, PredictionTiming

from ..feature import (
    BASE_CATALOG,
    CATALOG,
    FIELD_COMPARISON_NAMES,
    JOCKEY_NAMES,
    REGISTRATION_ABILITY_FEATURES,
    SPECIAL_RACE,
    UNAVAILABLE_NAMES,
)


def test_m_keeps_168_of_the_202_features_and_drops_the_34_unavailable_ones():
    assert len(ABILITY_FEATURES) == 202 and len(UNAVAILABLE_NAMES) == 34 and len(JOCKEY_NAMES) == 20
    assert len(REGISTRATION_ABILITY_FEATURES) == 168
    names = {feature.name for feature in REGISTRATION_ABILITY_FEATURES}
    # 騎手・枠番・馬番・馬場状態・馬体重・出走頭数・ブリンカー・持ち時計の順位は無い
    for name in ("騎手_勝率", "騎手_格上げ", "減量騎手", "frame_no", "body_weight", "field_size", "ブリンカーあり", "best_time_unit_rank", "馬番の位置"):
        assert name not in names
    # 調教師・血統・負担重量・調教・対戦の材料は残る
    for name in ("調教師_勝率", "父×芝ダ_3着内率", "carried", "坂路_4F最速14日", "指数_条件の重み", "ハンデ戦", "所属_栗東"):
        assert name in names


def test_the_catalog_has_180_numeric_features_known_from_the_registration_timing():
    assert len(BASE_CATALOG.names) == 176 and len(CATALOG.names) == 180
    assert set(CATALOG.names) - set(BASE_CATALOG.names) == set(ABILITY_SCORE_NAMES)
    assert SPECIAL_RACE in BASE_CATALOG.names and len(HEAD_TO_HEAD_FEATURES) == 7
    assert not CATALOG.categorical
    assert CATALOG.columns_for(PredictionTiming.THURSDAY) == CATALOG.names


def test_the_field_comparison_names_are_70_and_all_in_the_catalog():
    assert len(FIELD_COMPARISON_NAMES) == len(set(FIELD_COMPARISON_NAMES)) == 70
    assert set(FIELD_COMPARISON_NAMES) <= set(CATALOG.names)
    assert "騎手_勝率_順位" not in FIELD_COMPARISON_NAMES and "指数_条件の重み_順位" in FIELD_COMPARISON_NAMES
