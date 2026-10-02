"""この予想の特徴量（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜N）は ``yosou.shared.feature``。
ここには、手本（近走と適性）の新しい材料に K（重賞の傾向）を足した一覧と、K を作るクラスを置く。

| 名前 | 中身 |
|---|---|
| ``K_FEATURES`` | まとまり K の10個の一覧 |
| ``ABILITY_CATALOG`` | 木曜・前日のモデルの一覧（M・J に K を足したもの。木曜 201個・前日 213個） |
| ``RACE_DAY_CATALOG`` | 当日のモデルの一覧（手本の当日の 285個に K を足した 295個） |
| ``RACE_DAY_ABILITY_FEATURES`` | 当日のモデルが足す M（名前の重なる2つを除いた 200個） |
| ``StakesTendencyFeatures`` | K を作るクラス（``FeatureGroup`` を守る） |
| ``WIN_ODDS`` | 特徴量「単勝オッズ」の名前。予測の結果の表にも出すので、外にも見せる |
"""

from yosou.shared.feature.group import WIN_ODDS

from .feature_catalog import ABILITY_CATALOG, K_FEATURES, RACE_DAY_ABILITY_FEATURES, RACE_DAY_CATALOG
from .stakes_tendency_features import StakesTendencyFeatures

__all__ = ["ABILITY_CATALOG", "RACE_DAY_CATALOG", "RACE_DAY_ABILITY_FEATURES", "K_FEATURES", "StakesTendencyFeatures", "WIN_ODDS"]
