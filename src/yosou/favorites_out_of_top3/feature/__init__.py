"""この予想の特徴量の一覧（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜J）は ``yosou.shared.feature``。まとまり J（人気と人気の履歴）は
穴馬の予想とも共通なので、そこにある。ここには、A〜I に J を足した一覧だけを置く。

| 名前 | 中身 |
|---|---|
| ``CATALOG`` | この予想の特徴量 75個の一覧（``BASE_FEATURES`` + ``POPULARITY_FEATURES``） |
"""

from yosou.shared.feature import BASE_FEATURES, POPULARITY_FEATURES, FeatureCatalog

#: この予想の特徴量の一覧（まとまり A〜I と J）。
CATALOG = FeatureCatalog(BASE_FEATURES + POPULARITY_FEATURES)

__all__ = ["CATALOG"]
