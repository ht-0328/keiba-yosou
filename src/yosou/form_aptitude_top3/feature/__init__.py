"""この予想の特徴量（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜I）は ``yosou.shared.feature``。
ここには、この予想で足すまとまり J（市場の評価）と、A〜I に J を足した一覧を置く。

| 名前 | 中身 |
|---|---|
| ``MarketFeatures`` | まとまり J の3個（単勝オッズ・人気順位・オッズから見た勝率）を作る。``FeatureGroup`` を守る |
| ``J_FEATURES`` | まとまり J の3個の一覧（``feature_catalog.py``） |
| ``CATALOG`` | この予想の特徴量の一覧（``BASE_FEATURES`` + ``J_FEATURES``。当日は 74個） |
| ``WIN_ODDS`` | 特徴量「単勝オッズ」の名前。予測の結果の表にも出すので、外にも見せる |
"""

from .feature_catalog import CATALOG, J_FEATURES
from .market_features import WIN_ODDS, MarketFeatures

__all__ = ["CATALOG", "J_FEATURES", "MarketFeatures", "WIN_ODDS"]
