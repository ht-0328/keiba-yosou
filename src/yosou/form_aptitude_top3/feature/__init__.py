"""この予想の特徴量（設計書 09）。

特徴量を作るクラス（``FeatureBuilder``・まとまり A〜J）は ``yosou.shared.feature``。まとまり J（市場の評価）を作る
``MarketFeatures`` も、荒れ具合の予想と共通なので ``yosou.shared.feature.group`` に移した。
ここには、A〜I に J を足した一覧を置く。

| 名前 | 中身 |
|---|---|
| ``J_FEATURES`` | まとまり J の3個の一覧（共通の ``MARKET_FEATURES`` と同じもの） |
| ``CATALOG`` | この予想の特徴量の一覧（``BASE_FEATURES`` + ``J_FEATURES``。当日は 74個） |
| ``WIN_ODDS`` | 特徴量「単勝オッズ」の名前。予測の結果の表にも出すので、外にも見せる |
"""

from yosou.shared.feature.group import WIN_ODDS

from .feature_catalog import CATALOG, J_FEATURES

__all__ = ["CATALOG", "J_FEATURES", "WIN_ODDS"]
