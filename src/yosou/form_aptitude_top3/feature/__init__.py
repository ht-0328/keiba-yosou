"""この予想が使う特徴量の一覧（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜I）は ``yosou.shared.feature``。
この予想は、どの予想でも使う 71個（``BASE_FEATURES``）をそのまま使うので、一覧はそれで作る。

| 名前 | 中身 |
|---|---|
| ``CATALOG`` | この予想の特徴量 71個の一覧（``FeatureCatalog``） |
"""

from yosou.shared.feature import BASE_FEATURES, FeatureCatalog

#: この予想の特徴量の一覧（まとまり A〜I の 71個）。
CATALOG = FeatureCatalog(BASE_FEATURES)

__all__ = ["CATALOG"]
