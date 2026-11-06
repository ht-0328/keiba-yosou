"""当日の馬場傾向のレースの値（使う内の傾き・使う前の傾き）。本番の予想 ``yosou.local_upset_level`` に移した。ここからは同じ名前で使える。"""

from __future__ import annotations

from yosou.local_upset_level.feature.used_slope_features import FEATURES, NAMES, USED_FRONT, USED_INNER, UsedSlopeFeatures, race_slopes_table

__all__ = ["FEATURES", "NAMES", "USED_FRONT", "USED_INNER", "UsedSlopeFeatures", "race_slopes_table"]
