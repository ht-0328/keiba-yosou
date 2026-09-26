"""この予想の特徴量（設計書 09）。1頭ごとの特徴量は共通の ``FeatureBuilder``、1レースごとは共通の ``RaceFeatureBuilder`` が、
ここのまとまりのクラスを順に呼んで作る。

| 名前 | 中身 |
|---|---|
| ``EarlyHistoryFeatures`` | K. 序盤の位置取りの履歴（15個） |
| ``EarlyFieldComparisonFeatures`` | L. 同じレースの馬との比較（序盤）（9個） |
| ``CourseShapeFeatures`` | M. コースの形（3個） |
| ``ClosingHistoryFeatures`` | N. 末脚の履歴（10個） |
| ``ClosingFieldComparisonFeatures`` | O. 同じレースの馬との比較（末脚）（3個） |
| ``PaceMaterialFeatures`` | P. ペースの材料（1レースごと 10個） |
| ``PaceBaselineFeatures`` | Q. 前半タイムの基準とコース（1レースごと 6個） |
| ``LateMaterialFeatures`` | U. 後半の材料（1レースごと 7個） |
| ``EarlyForecastFeatures`` | S. 前半の予想の結果（1頭ごと 9個・1レースごと 6個） |
| ``LateForecastFeatures`` | T. 後半の予想の結果（7個） |
| ``GroupForecast`` | 1つの組（前半・後半・着順）の予測の入れ物と、その列の名前 |
| ``StackedColumns`` | 特徴量を予想ごとの一覧に合わせ、前の組の予測の列（S・T）を足す |
| ``RaceOrderStatistic`` | 同じレースの馬の値の、何番目に大きい（小さい）値 |
| ``feature_catalog.py`` | 特徴量の一覧（1回で作る ``HORSE_CATALOG``・``RACE_CATALOG`` と、予想ごとの一覧） |
| ``history/`` | 過去の記録から数える部品 |

R（レースの条件）は、共通の ``RaceConditionSummary`` をそのまま使う。
"""

from .closing_field_comparison_features import ClosingFieldComparisonFeatures
from .closing_history_features import ClosingHistoryFeatures
from .course_shape_features import CourseShapeFeatures
from .early_field_comparison_features import EarlyFieldComparisonFeatures
from .early_forecast_features import EarlyForecastFeatures
from .early_history_features import EarlyHistoryFeatures
from .feature_catalog import (
    EARLY_HORSE_CATALOG,
    EARLY_RACE_CATALOG,
    FINISH_CATALOG,
    FINISH_PLAIN_CATALOG,
    HORSE_CATALOG,
    LATE_HORSE_CATALOG,
    LATE_RACE_CATALOG,
    RACE_CATALOG,
)
from .group_forecast import (
    BACK_PROBABILITY,
    CLOSING_PREDICTION,
    CORNER4_PREDICTION,
    EVEN_PROBABILITY,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    MIDDLE_PROBABILITY,
    PLAIN_WIN_PROBABILITY,
    SECOND_HALF_QUANTILES,
    SLOW_PROBABILITY,
    WIN_PROBABILITY,
    GroupForecast,
)
from .late_forecast_features import LateForecastFeatures
from .late_material_features import LateMaterialFeatures
from .pace_baseline_features import PaceBaselineFeatures
from .pace_material_features import PaceMaterialFeatures
from .stacked_columns import StackedColumns

__all__ = [
    "EarlyHistoryFeatures", "EarlyFieldComparisonFeatures", "CourseShapeFeatures", "ClosingHistoryFeatures",
    "ClosingFieldComparisonFeatures", "PaceMaterialFeatures", "PaceBaselineFeatures", "LateMaterialFeatures",
    "EarlyForecastFeatures", "LateForecastFeatures", "GroupForecast", "StackedColumns",
    "HORSE_CATALOG", "RACE_CATALOG", "EARLY_HORSE_CATALOG", "EARLY_RACE_CATALOG", "LATE_HORSE_CATALOG",
    "LATE_RACE_CATALOG", "FINISH_CATALOG", "FINISH_PLAIN_CATALOG",
    "LEADER_PROBABILITY", "FRONT_PROBABILITY", "MIDDLE_PROBABILITY", "BACK_PROBABILITY",
    "SLOW_PROBABILITY", "EVEN_PROBABILITY", "HIGH_PROBABILITY", "FIRST_HALF_QUANTILES",
    "CORNER4_PREDICTION", "CLOSING_PREDICTION", "SECOND_HALF_QUANTILES", "WIN_PROBABILITY", "PLAIN_WIN_PROBABILITY",
]
