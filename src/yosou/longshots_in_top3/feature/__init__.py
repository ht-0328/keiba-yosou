"""この予想の特徴量の一覧（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜J）は ``yosou.shared.feature``。まとまり J（人気と人気の履歴）は
危険な人気馬の予想と共通なので、そこにある。ここには、A〜I に J を足した一覧だけを置く。
穴馬の区分は特徴量にしない（設計書 09 の「使わない特徴量」）。

| 名前 | 中身 |
|---|---|
| ``CATALOG`` | この予想の特徴量 78個の一覧（``BASE_FEATURES`` + ``POPULARITY_FEATURES`` + ``ODDS_FEATURES``） |
"""

from yosou.shared.feature import BASE_FEATURES, ODDS_FEATURES, POPULARITY_FEATURES, FeatureCatalog

#: この予想の特徴量の一覧（まとまり A〜I と J・K）。K（単勝オッズから見た評価）は前日から使う（既存モデルの修正計画の 1）。
CATALOG = FeatureCatalog(BASE_FEATURES + POPULARITY_FEATURES + ODDS_FEATURES)

__all__ = ["CATALOG"]
