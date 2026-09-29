"""この予想が使う特徴量の一覧（設計書 09）。

まとまり A〜I（``BASE_FEATURES``）と J（市場の評価）はどの予想でも同じで、この予想では
K（重賞の傾向）の10個を足す。K の作り方は ``stakes_tendency_features.py``。
"""

from __future__ import annotations

from yosou.shared.feature import BASE_FEATURES, MARKET_FEATURES, Feature, FeatureCatalog, FeatureKind, PredictionTiming

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

#: この予想の特徴量の一覧（A〜I の71個 + J の4個 + K の10個。当日は 85個）。
CATALOG = FeatureCatalog(BASE_FEATURES + MARKET_FEATURES + K_FEATURES)
