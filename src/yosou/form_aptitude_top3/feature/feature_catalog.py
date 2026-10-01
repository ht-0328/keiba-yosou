"""この予想が使う特徴量の一覧（設計書 09）。

まとまり A〜I（``BASE_FEATURES``）はどの予想でも同じで、この予想では J（市場の評価）の4個と、
L（騎手・調教師・血統の市場に対する成績）の4個を足す。L の記号は、穴馬・人気馬の予想（K まである）とそろえた。
"""

from __future__ import annotations

from yosou.shared.feature import BASE_FEATURES, MARKET_FEATURES, PEOPLE_MARKET_FEATURES, Feature, FeatureCatalog

#: J. 市場の評価（4個）。荒れ具合の予想とも共通なので、一覧は ``yosou.shared.feature`` にある。
J_FEATURES: tuple[Feature, ...] = MARKET_FEATURES

#: この予想の特徴量の一覧（まとまり A〜I と J・L。当日は 79個）。
CATALOG = FeatureCatalog(BASE_FEATURES + J_FEATURES + PEOPLE_MARKET_FEATURES)
