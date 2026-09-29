"""この予想の特徴量（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜J）は ``yosou.shared.feature``。
ここには、A〜J に K（重賞の傾向）を足した一覧と、K を作るクラスを置く。

| 名前 | 中身 |
|---|---|
| ``K_FEATURES`` | まとまり K の10個の一覧 |
| ``CATALOG`` | この予想の特徴量の一覧（A〜I + J + K。当日は 85個） |
| ``StakesTendencyFeatures`` | K を作るクラス（``FeatureGroup`` を守る） |
| ``WIN_ODDS`` | 特徴量「単勝オッズ」の名前。予測の結果の表にも出すので、外にも見せる |
"""

from yosou.shared.feature.group import WIN_ODDS

from .feature_catalog import CATALOG, K_FEATURES
from .stakes_tendency_features import StakesTendencyFeatures

__all__ = ["CATALOG", "K_FEATURES", "StakesTendencyFeatures", "WIN_ODDS"]
