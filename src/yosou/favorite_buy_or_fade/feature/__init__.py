"""この予想の特徴量の一覧（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜K）は ``yosou.shared.feature``。
ここには、手本の A〜I に、人気の履歴（J）と単勝オッズから見た評価（K）を足した一覧だけを置く。
前走の人気（前走も1番人気だったか）は、手本のまとまり D の「前走の人気」で分かる。

| 名前 | 中身 |
|---|---|
| ``CATALOG`` | この予想の特徴量 78個の一覧（``BASE_FEATURES`` + ``POPULARITY_FEATURES`` + ``ODDS_FEATURES``） |
"""

from yosou.shared.feature import BASE_FEATURES, ODDS_FEATURES, POPULARITY_FEATURES, FeatureCatalog

#: この予想の特徴量の一覧（まとまり A〜I と J・K）。
CATALOG = FeatureCatalog(BASE_FEATURES + POPULARITY_FEATURES + ODDS_FEATURES)

__all__ = ["CATALOG"]
