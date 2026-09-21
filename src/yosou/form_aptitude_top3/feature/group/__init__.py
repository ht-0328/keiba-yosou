"""特徴量のまとまり（設計書 09 の A〜I）ごとに1クラス。

| クラス | まとまり |
|---|---|
| ``RaceConditionFeatures`` | A. レースの条件（9個） |
| ``HorseFeatures`` | B. 馬のこと（9個） |
| ``PeopleFeatures`` | C. 騎手と調教師（6個） |
| ``PreviousRunFeatures`` | D. 前走（11個） |
| ``RecentFormFeatures`` | E. 近走のまとめ（10個） |
| ``AptitudeFeatures`` | F. この条件での経験（10個） |
| ``FieldComparisonFeatures`` | G. 同じレースの馬との比較（4個） |
| ``PedigreeFeatures`` | H. 血統（3個） |
| ``WorkoutFeatures`` | I. 調教（6個） |
"""

from .aptitude_features import AptitudeFeatures
from .field_comparison_features import FieldComparisonFeatures
from .horse_features import HorseFeatures
from .pedigree_features import PedigreeFeatures
from .people_features import PeopleFeatures
from .previous_run_features import PreviousRunFeatures
from .race_condition_features import RaceConditionFeatures
from .recent_form_features import RecentFormFeatures
from .workout_features import WorkoutFeatures

__all__ = [
    "RaceConditionFeatures", "HorseFeatures", "PeopleFeatures", "PreviousRunFeatures",
    "RecentFormFeatures", "AptitudeFeatures", "FieldComparisonFeatures", "PedigreeFeatures",
    "WorkoutFeatures",
]
