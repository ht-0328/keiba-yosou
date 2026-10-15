"""この予想の特徴量（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜N）は ``yosou.shared.feature``。
ここには、手本（近走と適性）の材料に K（重賞の傾向）を足した一覧と、K を作るクラスを置く。

| 名前 | 中身 |
|---|---|
| ``K_FEATURES`` | まとまり K の51個の一覧 |
| ``CUTS``・``TendencyCut``・``STATS`` | K の12個の切り口（自分と同じ条件だった馬の条件）と、切り口ごとに数える4つの成績の名前 |
| ``ABILITY_CATALOG`` | 木曜・前日のモデルの一覧（M・O・J に K を足したもの。木曜 238個・前日 261個） |
| ``RACE_DAY_CATALOG`` | 当日のモデルの一覧（手本の当日の 285個に K を足した 336個） |
| ``RACE_DAY_ABILITY_FEATURES`` | 当日のモデルが足す M（名前の重なる2つを除いた 200個） |
| ``StakesTendencyFeatures`` | K を作るクラス（``FeatureGroup`` を守る）。帯分けは ``ConditionBands``、数え上げは ``EditionStats`` |
| ``WIN_ODDS`` | 特徴量「単勝オッズ」の名前。予測の結果の表にも出すので、外にも見せる |
"""

from yosou.shared.feature.group import WIN_ODDS

from .condition_bands import ConditionBands
from .edition_stats import EditionStats
from .feature_catalog import ABILITY_CATALOG, K_FEATURES, RACE_DAY_ABILITY_FEATURES, RACE_DAY_CATALOG
from .stakes_tendency_features import StakesTendencyFeatures
from .tendency_cut import CUTS, STATS, TendencyCut, cut_keyed

__all__ = ["ABILITY_CATALOG", "RACE_DAY_CATALOG", "RACE_DAY_ABILITY_FEATURES", "K_FEATURES", "CUTS", "STATS", "TendencyCut",
           "cut_keyed", "ConditionBands", "EditionStats", "StakesTendencyFeatures", "WIN_ODDS"]
