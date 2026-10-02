"""この予想が使う特徴量の一覧（設計書 09）。

手本（近走と適性から3着以内を予想）の新しい材料と同じ構成に、K（重賞の傾向）の10個を足す（設計書 15 の 9）。

- 馬の力の材料（木曜・前日）: M（202個）・O（対戦レーティング。7個）と J（市場の評価。前日から）に K を足す（``ABILITY_CATALOG``）。
- 当日の材料: 手本の当日と同じ A〜L（79個）・N（券種ごとの支持。6個）・M のうち名前の重ならない 200個に、K を足す
  （``RACE_DAY_CATALOG``。295個）。

K の作り方は ``stakes_tendency_features.py``。
"""

from __future__ import annotations

from yosou.shared.feature import (
    ABILITY_FEATURES,
    BASE_FEATURES,
    HEAD_TO_HEAD_FEATURES,
    MARKET_FEATURES,
    PEOPLE_MARKET_FEATURES,
    POOL_SUPPORT_FEATURES,
    Feature,
    FeatureCatalog,
    FeatureKind,
    PredictionTiming,
)

_N = FeatureKind.NUMERIC
_DAY_BEFORE = PredictionTiming.DAY_BEFORE

#: K. 重賞の傾向（10個）。そのレースより前の開催だけから数えた「縮めたずれ」（設計書 09 の K）。
#: 枠を使うものだけ、枠番の決まる前日から。
K_FEATURES: tuple[Feature, ...] = (
    Feature("重賞の過去開催の数", "K", _N),
    Feature("上位人気の信頼度のずれ", "K", _N),
    Feature("1番人気の信頼度のずれ", "K", _N),
    Feature("前に行く馬のずれ", "K", _N),
    Feature("前に行く馬のずれ×前に行くか", "K", _N),
    Feature("内枠のずれ", "K", _N),
    Feature("内枠のずれ×枠の内寄り", "K", _N, _DAY_BEFORE),
    Feature("休み明けのずれ×休み明けか", "K", _N),
    Feature("関西馬のずれ×関西馬か", "K", _N),
    Feature("好走経験者のずれ×好走経験があるか", "K", _N),
)

#: 手本の当日の材料のうち、M を除いた部分（A〜I・J・L の 79個と N の6個）。
_FORM_RACE_DAY_FEATURES: tuple[Feature, ...] = BASE_FEATURES + MARKET_FEATURES + PEOPLE_MARKET_FEATURES + POOL_SUPPORT_FEATURES

#: 当日のモデルが足す M（手本と同じく、A〜L・N と同じ名前の2つ（前走からの日数・芝ダ替わり）を除いた 200個）。
RACE_DAY_ABILITY_FEATURES: tuple[Feature, ...] = tuple(
    feature for feature in ABILITY_FEATURES
    if feature.name not in {feature.name for feature in _FORM_RACE_DAY_FEATURES}
)

#: 馬の力の材料の一覧（木曜・前日のモデル。手本と同じ M・O・J に K を足したもの。木曜は 199 + 9 = 208個、前日は 210 + 10 = 220個）。
ABILITY_CATALOG = FeatureCatalog(ABILITY_FEATURES + HEAD_TO_HEAD_FEATURES + MARKET_FEATURES + K_FEATURES)

#: 当日のモデルの一覧（手本の当日の 285個に K の10個を足した 295個）。
RACE_DAY_CATALOG = FeatureCatalog(_FORM_RACE_DAY_FEATURES + RACE_DAY_ABILITY_FEATURES + K_FEATURES)
