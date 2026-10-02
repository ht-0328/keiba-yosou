"""この予想の特徴量（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜N）は ``yosou.shared.feature``。まとまり J（市場の評価）を作る
``MarketFeatures`` も、荒れ具合の予想と共通なので ``yosou.shared.feature.group`` に移した。
ここには、この予想が使う一覧を置く。

| 名前 | 中身 |
|---|---|
| ``J_FEATURES`` | まとまり J の4個の一覧（共通の ``MARKET_FEATURES`` と同じもの） |
| ``CATALOG`` | 今の材料の一覧（``BASE_FEATURES`` + J + L。当日は 79個）。当日に券種のオッズが無いときのモデルの一覧でもある |
| ``POOL_CATALOG`` | 今の材料に N を足した一覧（当日は 85個。前日は N を使わない） |
| ``RACE_DAY_CATALOG`` | 当日のモデルの一覧（``POOL_CATALOG`` に M のうち今の材料と名前の重ならない 200個を足した 285個。``RACE_DAY_ABILITY_FEATURES``） |
| ``ABILITY_CATALOG`` | 馬の力の材料の一覧（M + O + J。木曜は M のうち木曜に分かる 192個と O の7個） |
| ``POOL_SUPPORT_NAMES`` | まとまり N の6個の名前（券種のオッズが無いかを確かめるのに使う） |
| ``WIN_ODDS`` | 特徴量「単勝オッズ」の名前。予測の結果の表にも出すので、外にも見せる |
"""

from yosou.shared.feature import POOL_SUPPORT_NAMES
from yosou.shared.feature.group import WIN_ODDS

from .feature_catalog import (
    ABILITY_CATALOG,
    CATALOG,
    J_FEATURES,
    POOL_CATALOG,
    RACE_DAY_ABILITY_FEATURES,
    RACE_DAY_CATALOG,
)

__all__ = ["CATALOG", "POOL_CATALOG", "RACE_DAY_CATALOG", "RACE_DAY_ABILITY_FEATURES", "ABILITY_CATALOG", "J_FEATURES", "POOL_SUPPORT_NAMES", "WIN_ODDS"]
