"""この予想の特徴量の一覧（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜J）は ``yosou.shared.feature``。まとまり J（人気と人気の履歴）は
穴馬の予想とも共通なので、そこにある。ここには、A〜I に J・K・L を足した一覧だけを置く。

| 名前 | 中身 |
|---|---|
| ``CATALOG`` | この予想の特徴量 82個の一覧（``BASE_FEATURES`` + ``POPULARITY_FEATURES`` + ``ODDS_FEATURES`` + ``PEOPLE_MARKET_FEATURES``） |
"""

from yosou.shared.feature import BASE_FEATURES, ODDS_FEATURES, PEOPLE_MARKET_FEATURES, POPULARITY_FEATURES, FeatureCatalog

#: この予想の特徴量の一覧（まとまり A〜I と J・K・L）。K（単勝オッズから見た評価）は前日から使う（既存モデルの修正計画の 1）。
#: L（騎手・調教師・血統の市場に対する成績）は木曜から使う（2026-09-30 に採用）。
CATALOG = FeatureCatalog(BASE_FEATURES + POPULARITY_FEATURES + ODDS_FEATURES + PEOPLE_MARKET_FEATURES)

__all__ = ["CATALOG"]
