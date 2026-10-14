"""この予想が使う特徴量の一覧（設計書 09）。

中央の予想の馬の力の材料（M）202個から、特別登録の時点に無い 34個（枠番・馬番・馬場状態・馬体重を使う 10個、騎手を使う 20個、
出走頭数、ブリンカー、持ち時計の順位 2個）を外した 168個に、対戦レーティング（O）の7個と特別競走の印（Y）の1個を足して
``FeatureBuilder`` で作り、能力スコア（T）の4個は ``AbilityScoreAttachment`` で学習データ・予測用データに足す。合わせて 180個。
どれも数値で、特別登録の時点（``thursday`` の枠）から分かる。
"""

from __future__ import annotations

from yosou.ability_score import ABILITY_SCORE_FEATURES
from yosou.ability_score.features import DEVIATION, GAP_TO_SECOND, RANK
from yosou.shared.feature import ABILITY_FEATURES, HEAD_TO_HEAD_FEATURES, Feature, FeatureCatalog, FeatureKind
from yosou.shared.feature.ability.ability_columns import (
    DAY_BEFORE_COLUMNS,
    RACE_DAY_COLUMNS,
    RECORD_SUFFIXES,
    RELATIVE_COLUMNS,
    RELATIVE_SUFFIXES,
)
from yosou.shared.feature.head_to_head.head_to_head_columns import FIELD_GAP, FIELD_RANK, FIELD_Z

#: 騎手を使う通算の成績の区分と、レース内の比べの元の列。
_JOCKEY_RECORD_GROUPS: tuple[str, ...] = ("騎手", "騎手×競馬場", "騎手×調教師")
_JOCKEY_RELATIVE_BASES: tuple[str, ...] = ("騎手_勝率", "騎手_1年_勝率")
#: 騎手が決まっていないので使えない 20個（設計書 09 の「外す 34個の内訳」）。
JOCKEY_NAMES: tuple[str, ...] = (
    "騎手_前走と同じ",
    *(f"{group}_{suffix}" for group in _JOCKEY_RECORD_GROUPS for suffix in RECORD_SUFFIXES),
    "騎手_1年_勝率", "騎手_1年_3着内率", "騎手_格上げ",
    *(f"{base}_{suffix}" for base in _JOCKEY_RELATIVE_BASES for suffix in RELATIVE_SUFFIXES),
    "減量騎手",
)
#: 出走頭数（登録頭数とは別のもの）、ブリンカー（出走馬名表から分かる）、持ち時計の順位（馬場状態が要る）。
_OTHER_UNAVAILABLE: tuple[str, ...] = ("field_size", "ブリンカーあり", "best_time_unit_rank", "best_time_dist_rank")
#: M のうち、特別登録の時点に無い 34個。
UNAVAILABLE_NAMES: frozenset[str] = frozenset({*DAY_BEFORE_COLUMNS, *RACE_DAY_COLUMNS, *JOCKEY_NAMES, *_OTHER_UNAVAILABLE})
#: M のうち、この予想が使う 168個（名前は共通の ``ABILITY_FEATURES`` のまま）。
REGISTRATION_ABILITY_FEATURES: tuple[Feature, ...] = tuple(
    feature for feature in ABILITY_FEATURES if feature.name not in UNAVAILABLE_NAMES
)
REGISTRATION_ABILITY_NAMES: tuple[str, ...] = tuple(feature.name for feature in REGISTRATION_ABILITY_FEATURES)

#: Y. 特別競走の印（1個）。競走名の付いたレースなら 1、平場なら 0。作るのは ``SpecialRaceFeatures``。
SPECIAL_RACE = "特別競走か"
SPECIAL_RACE_FEATURES: tuple[Feature, ...] = (Feature(SPECIAL_RACE, "Y", FeatureKind.NUMERIC),)

#: ``FeatureBuilder`` が記録から作る一覧（M 168個・O 7個・Y 1個の 176個）。
BASE_CATALOG = FeatureCatalog(REGISTRATION_ABILITY_FEATURES + HEAD_TO_HEAD_FEATURES + SPECIAL_RACE_FEATURES)
#: この予想の特徴量の一覧（180個）。T の4個は ``AbilityScoreAttachment`` が学習データ・予測用データに足す。
CATALOG = FeatureCatalog(BASE_CATALOG.features + ABILITY_SCORE_FEATURES)

#: 同じレースの相手と比べる材料の 70個（設計書 09 の「相手と比べる材料」）。``FieldComparisonFreeData`` が外すのに使う。
#: M のレース内の比べ 60個（騎手の2列を除く 20列 × 順位・最良との差・偏差）・先頭率の合計 2個・セリの価格の比べ 2個・O の3個・T の3個。
FIELD_COMPARISON_NAMES: tuple[str, ...] = (
    *(f"{column}_{suffix}" for column in RELATIVE_COLUMNS if column not in _JOCKEY_RELATIVE_BASES
      for suffix in RELATIVE_SUFFIXES),
    "先頭率の合計", "ほかの馬の先頭率の合計", "セリの価格のレース内順位", "セリの価格とレースの最高との差",
    FIELD_RANK, FIELD_Z, FIELD_GAP, DEVIATION, GAP_TO_SECOND, RANK,
)
