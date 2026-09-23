"""この予想の特徴量（設計書 09）。1頭ごとの特徴量をレース単位に集約して作る。

1頭ごとの特徴量を作るクラス（``FeatureBuilder``・まとまり A〜J）と、レース単位に集約する入口（``RaceFeatureBuilder``）は
``yosou.shared.feature``。ここには、まとまり A〜E を集約するクラスと、一覧を置く。

| 名前 | 中身 |
|---|---|
| ``RaceConditionSummary`` | A. レースの条件（11個）。レースの1頭目の値と、特別戦か・ハンデ戦か |
| ``OddsShapeFeatures`` | B. オッズの形（10個）。1番人気のオッズ、2〜5番人気の最大オッズ、10倍未満の頭数 など |
| ``FieldStrengthSpreadFeatures`` | C. 出走馬の実績のばらつき（10個） |
| ``FavoriteRiskFeatures`` | D. 1番人気の危うさ（10個）。単勝オッズが最小の馬の値 |
| ``ConditionUpsetRateFeatures`` | E. 過去の同条件の荒れ率（8個）。券種ごと |
| ``distance_band()`` | 距離を距離帯にする関数 |
| ``HORSE_CATALOG`` | 集約の元になる1頭ごとの特徴量の一覧（A〜I と J。75個） |
| ``CATALOG`` | この予想の特徴量の一覧（A〜E。当日は 49個） |

``GOING``（馬場状態）・``FAVORITE_ODDS``（1番人気のオッズ）・``FAVORITE_WEIGHT_CHANGE``（1番人気の馬体重の増減）は、
予測に要る情報の確認に使うので、外にも見せる。
"""

from .condition_upset_rate_features import ConditionUpsetRateFeatures, class_rate_name, course_rate_name
from .distance_band import distance_band
from .favorite_risk_features import FAVORITE_WEIGHT_CHANGE, FavoriteRiskFeatures
from .feature_catalog import CATALOG, HORSE_CATALOG, RACE_FEATURES
from .field_strength_spread_features import FieldStrengthSpreadFeatures
from .odds_shape_features import FAVORITE_ODDS, UPPER_MAX_ODDS, OddsShapeFeatures
from .race_condition_summary import GOING, RaceConditionSummary

__all__ = [
    "RaceConditionSummary", "OddsShapeFeatures", "FieldStrengthSpreadFeatures", "FavoriteRiskFeatures",
    "ConditionUpsetRateFeatures", "distance_band", "course_rate_name", "class_rate_name",
    "HORSE_CATALOG", "CATALOG", "RACE_FEATURES",
    "GOING", "FAVORITE_ODDS", "UPPER_MAX_ODDS", "FAVORITE_WEIGHT_CHANGE",
]
