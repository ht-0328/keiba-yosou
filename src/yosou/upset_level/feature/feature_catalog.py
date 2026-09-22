"""この予想が使う特徴量の一覧（設計書 09）。

1頭ごとの一覧（``HORSE_CATALOG``。手本と同じ A〜I に J（市場の評価）を足した 74個）は、レース単位に集約する元になる。
レース単位の一覧（``CATALOG``。A〜E の 49個）が、モデルに渡す特徴量である。
"""

from __future__ import annotations

from yosou.shared.feature import BASE_FEATURES, MARKET_FEATURES, Feature, FeatureCatalog, FeatureKind, PredictionTiming

from . import (
    condition_upset_rate_features as e,
    favorite_risk_features as d,
    field_strength_spread_features as c,
    odds_shape_features as b,
    race_condition_summary as a,
)

_N = FeatureKind.NUMERIC
_C = FeatureKind.CATEGORICAL
#: 前日から分かる（馬場状態・オッズ）。当日から分かる（馬体重）。
_DAY_BEFORE = PredictionTiming.DAY_BEFORE
_RACE_DAY = PredictionTiming.RACE_DAY

#: 1頭ごとの特徴量の一覧（集約の元。当日は 74個）。
HORSE_CATALOG = FeatureCatalog(BASE_FEATURES + MARKET_FEATURES)

#: レース単位の特徴量 49個。並びは設計書 09 の表の順。時点を書いていないものは木曜から分かる。
RACE_FEATURES: tuple[Feature, ...] = (
    # A. レースの条件（11個）
    Feature("競馬場", "A", _C),
    Feature("芝ダ", "A", _C),
    Feature("コース", "A", _C),
    Feature("距離", "A", _N),
    Feature(a.GOING, "A", _C, _DAY_BEFORE),
    Feature("クラス", "A", _N),
    Feature(a.FIELD_SIZE, "A", _N),
    Feature("開催月", "A", _N),
    Feature("牡馬と牝馬が一緒に走るか", "A", _C),
    Feature(a.SPECIAL_RACE, "A", _C),
    Feature(a.HANDICAP, "A", _C),
    # B. オッズの形（10個）。前日から
    *(Feature(name, "B", _N, _DAY_BEFORE) for name in b.NAMES),
    # C. 出走馬の実績のばらつき（10個）。持ち時計だけ前日から
    *(Feature(name, "C", _N, _DAY_BEFORE if name == c.TIMED_SHARE else PredictionTiming.THURSDAY) for name in c.NAMES),
    # D. 1番人気の危うさ（10個）。前日から。馬体重の増減は当日から
    Feature(d.FAVORITE_PREV_FINISH, "D", _N, _DAY_BEFORE),
    Feature(d.FAVORITE_PREV_POPULARITY, "D", _N, _DAY_BEFORE),
    Feature(d.FAVORITE_PREV_GAP, "D", _N, _DAY_BEFORE),
    Feature(d.FAVORITE_RECENT_FINISH, "D", _N, _DAY_BEFORE),
    Feature(d.FAVORITE_WORSE_COUNT, "D", _N, _DAY_BEFORE),
    Feature(d.FAVORITE_CAREER_RUNS, "D", _N, _DAY_BEFORE),
    Feature(d.FAVORITE_JOCKEY_CHANGE, "D", _C, _DAY_BEFORE),
    Feature(d.FAVORITE_DISTANCE_CHANGE, "D", _C, _DAY_BEFORE),
    Feature(d.FAVORITE_CLASS_CHANGE, "D", _C, _DAY_BEFORE),
    Feature(d.FAVORITE_WEIGHT_CHANGE, "D", _N, _RACE_DAY),
    # E. 過去の同条件の荒れ率（8個）
    *(Feature(name, "E", _N) for name in e.NAMES),
)

#: この予想の特徴量の一覧（モデルに渡す。当日は 49個）。
CATALOG = FeatureCatalog(RACE_FEATURES)
