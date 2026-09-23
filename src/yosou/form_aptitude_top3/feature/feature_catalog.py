"""この予想が使う特徴量の一覧（設計書 09）。

まとまり A〜I（``BASE_FEATURES``）はどの予想でも同じで、この予想では J（市場の評価）の4個を足す。
"""

from __future__ import annotations

from yosou.shared.feature import BASE_FEATURES, MARKET_FEATURES, Feature, FeatureCatalog

#: J. 市場の評価（3個）。荒れ具合の予想とも共通なので、一覧は ``yosou.shared.feature`` にある。
J_FEATURES: tuple[Feature, ...] = MARKET_FEATURES

#: この予想の特徴量の一覧（まとまり A〜I と J。当日は 75個）。
CATALOG = FeatureCatalog(BASE_FEATURES + J_FEATURES)
