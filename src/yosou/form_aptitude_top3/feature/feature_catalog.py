"""この予想が使う特徴量の一覧（設計書 09）。

まとまり A〜I（``BASE_FEATURES``）はどの予想でも同じで、この予想では J（市場の評価）の3個を足す。
"""

from __future__ import annotations

from yosou.shared.feature import BASE_FEATURES, Feature, FeatureCatalog, FeatureKind, PredictionTiming

from .market_features import MARKET_WIN_RATE, POPULARITY_RANK, WIN_ODDS

_N = FeatureKind.NUMERIC
#: オッズが分かるのは、前日発売が始まる前日から（設計書 07）。木曜は使わない。
_DAY_BEFORE = PredictionTiming.DAY_BEFORE

#: J. 市場の評価（3個）。どれも大小に意味がある数なので、数値特徴量にする（設計書 12 の 1）。
J_FEATURES: tuple[Feature, ...] = (
    Feature(WIN_ODDS, "J", _N, _DAY_BEFORE),
    Feature(POPULARITY_RANK, "J", _N, _DAY_BEFORE),
    Feature(MARKET_WIN_RATE, "J", _N, _DAY_BEFORE),
)

#: この予想の特徴量の一覧（まとまり A〜I と J。当日は 74個）。
CATALOG = FeatureCatalog(BASE_FEATURES + J_FEATURES)
