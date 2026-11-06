"""この予想が使う特徴量の一覧（設計書 09）。

1頭ごとの一覧（``HORSE_CATALOG``。地方の土台 A〜H に J（市場の評価）を足したもの）は、レース単位に集約する元になる。
レース単位の一覧（``CATALOG``。中央の荒れ具合の A〜E 49個 ＋ 当日の馬場傾向のレースの値 U 2個）が、モデルに渡す特徴量である。
"""

from __future__ import annotations

from yosou.local_form_aptitude_top3.feature import LOCAL_BASE_FEATURES
from yosou.shared.feature import MARKET_FEATURES, FeatureCatalog
from yosou.upset_level.feature import RACE_FEATURES

from .used_slope_features import FEATURES as USED_SLOPE_FEATURES

#: 1頭ごとの特徴量の一覧（集約の元。地方の土台 A〜H ＋ J。調教は地方競馬DATA に無い）。
HORSE_CATALOG = FeatureCatalog(LOCAL_BASE_FEATURES + MARKET_FEATURES)
#: この予想の特徴量の一覧（モデルに渡す。当日は 51個: 中央の 49個 ＋ U 2個。出馬表 27個・前日 48個）。
CATALOG = FeatureCatalog(RACE_FEATURES + USED_SLOPE_FEATURES)
