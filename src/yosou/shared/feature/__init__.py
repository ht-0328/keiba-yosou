"""特徴量を作る（設計書 09）。学習データも予測用データも、ここの同じクラスで作る（設計書 11 の 4）。

| 場所 | 中身 |
|---|---|
| ``feature_catalog.py`` | どの予想でも使う 71個の一覧（``BASE_FEATURES``）、人気を使う予想が足す4個（``POPULARITY_FEATURES``）、オッズを使う予想が足す3個（``MARKET_FEATURES``）、予想ごとの一覧（``FeatureCatalog``） |
| ``Feature``・``FeatureKind`` | 一覧の1行と、その型 |
| ``FeatureGroup`` | まとまりのクラスに共通の決まり（インターフェース。1頭ごと） |
| ``RaceFeatureGroup`` | レース単位のまとまりのクラスに共通の決まり（インターフェース） |
| ``PredictionTiming`` | 予測する時点（木曜・前日・当日）と、その時点で分からない特徴量 |
| ``EntryRecords`` | 特徴量を作る元の記録の入れ物（1頭ごと） |
| ``RaceRecords`` | レース単位の特徴量を作る元の記録の入れ物（1頭ごとの特徴量と払戻を含む） |
| ``EntryColumns`` | 記録から列を選び、名前を付け直す |
| ``FeatureBuilder`` | 入口（1頭ごと）。まとまりごとのクラスを順に呼んで、1つの表にする |
| ``RaceFeatureBuilder`` | 入口（レース単位）。1頭ごとの特徴量を作ってから、まとまりごとに集約する（荒れ具合の設計書 05 の図3） |
| ``group/`` | 1頭ごとのまとまり A〜J ごとに1クラス（J は人気かオッズを使う予想だけが渡す） |
| ``history/`` | 過去の記録から数える部品（開催日より前のものだけを使う決まりを、ここで守る） |
| ``as_numbers``・``typed_features`` | 数の列を小数の列にする関数と、特徴量の表の型をそろえる関数（欠損値のそろえ方を1か所にする） |

予想ごとの一覧は、その予想のパッケージで ``FeatureCatalog(BASE_FEATURES)`` のように作る。
"""

from .entry_columns import EntryColumns
from .entry_records import EntryRecords
from .feature import Feature
from .feature_builder import FeatureBuilder
from .feature_catalog import BASE_FEATURES, MARKET_FEATURES, POPULARITY_FEATURES, FeatureCatalog
from .feature_group import FeatureGroup
from .feature_kind import FeatureKind
from .history import RecentRunSummary, WorkoutCoverage
from .prediction_timing import PredictionTiming
from .race_feature_builder import RaceFeatureBuilder
from .race_feature_group import RaceFeatureGroup
from .race_records import RaceRecords
from .time_windows import PEOPLE_WINDOW_DAYS, WORKOUT_WINDOW_DAYS
from .value_types import as_numbers, as_yes_no, typed_features

__all__ = [
    "FeatureBuilder", "RaceFeatureBuilder", "EntryRecords", "RaceRecords", "EntryColumns", "PredictionTiming",
    "WorkoutCoverage", "RecentRunSummary",
    "BASE_FEATURES", "POPULARITY_FEATURES", "MARKET_FEATURES", "FeatureCatalog", "Feature", "FeatureKind",
    "FeatureGroup", "RaceFeatureGroup",
    "WORKOUT_WINDOW_DAYS", "PEOPLE_WINDOW_DAYS", "as_numbers", "as_yes_no", "typed_features",
]
