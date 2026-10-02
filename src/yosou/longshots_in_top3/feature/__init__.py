"""この予想の特徴量の一覧と、この予想だけのまとまり M（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜L）は ``yosou.shared.feature``。まとまり J（人気と人気の履歴）と
K（単勝オッズから見た評価）は危険な人気馬の予想と、L（騎手・調教師・血統の市場に対する成績）は全頭の予想と共通なので、
そこにある。ここには、A〜L に M を足した一覧と、この予想だけが使う M を作るクラスを置く。
穴馬の区分は特徴量にしない（設計書 09 の「使わない特徴量」）。

| 名前 | 中身 |
|---|---|
| ``CATALOG`` | この予想の特徴量 86個の一覧（``BASE_FEATURES`` + ``POPULARITY_FEATURES`` + ``ODDS_FEATURES`` + ``PEOPLE_MARKET_FEATURES`` + ``PLACE_ODDS_FEATURES``） |
| ``PLACE_ODDS_FEATURES`` | M. 複勝オッズから見た評価（4個）の一覧（``place_odds_catalog.py``） |
| ``PlaceOddsFeatures`` | M を作る（``FeatureGroup`` を守る） |
| ``PlaceMarketRate`` | 複勝オッズから見た3着以内率を出す（M の1つ） |
"""

from yosou.shared.feature import BASE_FEATURES, ODDS_FEATURES, PEOPLE_MARKET_FEATURES, POPULARITY_FEATURES, FeatureCatalog

from .place_market_rate import PlaceMarketRate
from .place_odds_catalog import (
    PLACE_MARKET_RATE,
    PLACE_ODDS_FEATURES,
    PLACE_ODDS_HIGH_FEATURE,
    PLACE_ODDS_LOW_FEATURE,
    PLACE_TO_WIN_RATIO,
)
from .place_odds_features import PlaceOddsFeatures

#: この予想の特徴量の一覧（まとまり A〜I と J・K・L・M）。K（単勝オッズから見た評価）と M（複勝オッズから見た評価）は
#: 前日から使う（既存モデルの修正計画の 1・設計書 15 の 16）。L（騎手・調教師・血統の市場に対する成績）は木曜から使う
#: （2026-09-30 に採用）。
CATALOG = FeatureCatalog(
    BASE_FEATURES + POPULARITY_FEATURES + ODDS_FEATURES + PEOPLE_MARKET_FEATURES + PLACE_ODDS_FEATURES
)

__all__ = [
    "CATALOG", "PLACE_ODDS_FEATURES", "PlaceOddsFeatures", "PlaceMarketRate",
    "PLACE_ODDS_LOW_FEATURE", "PLACE_ODDS_HIGH_FEATURE", "PLACE_MARKET_RATE", "PLACE_TO_WIN_RATIO",
]
