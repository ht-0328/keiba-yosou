"""この予想の特徴量（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜I）は ``yosou.shared.feature``。
ここには、この予想で足すまとまり J と、A〜I に J を足した一覧を置く。

| 名前 | 中身 |
|---|---|
| ``PopularityHistoryFeatures`` | まとまり J の4個を作る。``FeatureGroup`` を守る |
| ``J_FEATURES`` | まとまり J の4個の一覧（``feature_catalog.py``） |
| ``CATALOG`` | この予想の特徴量の一覧（``BASE_FEATURES`` + ``J_FEATURES``） |
| ``POPULARITY_RANK`` | 特徴量「人気順位」の名前。予測の結果の表にも出すので、外にも見せる |

過去走から近5走の人気を数える部品は ``history/``。
"""

from .feature_catalog import CATALOG, J_FEATURES
from .popularity_history_features import POPULARITY_RANK, PopularityHistoryFeatures

__all__ = ["CATALOG", "J_FEATURES", "PopularityHistoryFeatures", "POPULARITY_RANK"]
