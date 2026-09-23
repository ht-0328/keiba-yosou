"""特徴量のまとまり（設計書 09 の A〜J）ごとに1クラス。

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
| ``PopularityHistoryFeatures`` | J. 人気と人気の履歴（4個）。人気を使う予想だけが渡す |
| ``MarketFeatures`` | J. 市場の評価（4個）。オッズを使う予想だけが渡す |
| ``OddsFeatures`` | K. 単勝オッズから見た評価（3個）。人気を使う予想が、オッズも使うときに渡す |

``POPULARITY_RANK`` は特徴量「人気順位」、``WIN_ODDS`` は「単勝オッズ」の名前。予測の結果の表にも出すので、外にも見せる。
"""

from .aptitude_features import AptitudeFeatures
from .field_comparison_features import FieldComparisonFeatures
from .horse_features import HorseFeatures
from .market_features import MARKET_WIN_RATE, MarketFeatures
from .odds_features import WIN_ODDS, OddsFeatures
from .pedigree_features import PedigreeFeatures
from .people_features import PeopleFeatures
from .popularity_history_features import POPULARITY_RANK, PopularityHistoryFeatures
from .previous_run_features import PreviousRunFeatures
from .race_condition_features import RaceConditionFeatures
from .recent_form_features import RecentFormFeatures
from .workout_features import WorkoutFeatures

__all__ = [
    "RaceConditionFeatures", "HorseFeatures", "PeopleFeatures", "PreviousRunFeatures",
    "RecentFormFeatures", "AptitudeFeatures", "FieldComparisonFeatures", "PedigreeFeatures",
    "WorkoutFeatures", "PopularityHistoryFeatures", "POPULARITY_RANK",
    "MarketFeatures", "OddsFeatures", "WIN_ODDS", "MARKET_WIN_RATE",
]
