"""この予想が使う特徴量の一覧（設計書 09）。

まとまり A〜I（``BASE_FEATURES``）は手本の予想と同じで、この予想では J（人気と人気の履歴）の4個を足す。
"""

from __future__ import annotations

from yosou.shared.feature import BASE_FEATURES, Feature, FeatureCatalog, FeatureKind

from .history import AVERAGE_POPULARITY, WORSE_THAN_POPULARITY
from .popularity_history_features import POPULARITY_RANK, PREV_POPULARITY_GAP

_N = FeatureKind.NUMERIC

#: J. 人気と人気の履歴（4個）。どれも大小に意味がある数なので、数値特徴量にする（設計書 12 の 1）。
J_FEATURES: tuple[Feature, ...] = (
    Feature(POPULARITY_RANK, "J", _N),
    Feature(PREV_POPULARITY_GAP, "J", _N),
    Feature(WORSE_THAN_POPULARITY, "J", _N),
    Feature(AVERAGE_POPULARITY, "J", _N),
)

#: この予想の特徴量の一覧（まとまり A〜I と J）。
CATALOG = FeatureCatalog(BASE_FEATURES + J_FEATURES)
