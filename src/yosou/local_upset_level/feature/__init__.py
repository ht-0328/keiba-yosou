"""この予想の特徴量（設計書 09）。

レース単位のまとまり A〜E（49個）を集約するクラスと一覧は、中央の荒れ具合の ``yosou.upset_level.feature``。
ここには、地方で足す当日の馬場傾向のレースの値（U。2個）と、この予想の一覧を置く。

| 名前 | 中身 |
|---|---|
| ``HORSE_CATALOG`` | 集約の元になる1頭ごとの特徴量の一覧（地方の土台 A〜H ＋ J。調教は無い） |
| ``CATALOG`` | この予想の特徴量の一覧（中央の荒れ具合の 49個 ＋ U 2個。当日は 51個） |
| ``UsedSlopeFeatures``・``race_slopes_table()``・``USED_SLOPE_NAMES`` | 当日の馬場傾向のレースの値（使う内の傾き・使う前の傾き）を、レース単位の特徴量にする（``RaceFeatureGroup`` を守る）。表は 1行 = 1頭の U の表からレースごとに取る |
| ``RaceUsedSlopes`` | これから走る1レースの使う傾きを、``UsedSlopeFeatures`` に渡す表（1行）にする（予測用） |
"""

from .feature_catalog import CATALOG, HORSE_CATALOG
from .race_used_slopes import RaceUsedSlopes
from .used_slope_features import FEATURES as USED_SLOPE_FEATURES, NAMES as USED_SLOPE_NAMES, UsedSlopeFeatures, race_slopes_table

__all__ = ["CATALOG", "HORSE_CATALOG", "UsedSlopeFeatures", "race_slopes_table", "USED_SLOPE_FEATURES", "USED_SLOPE_NAMES", "RaceUsedSlopes"]
