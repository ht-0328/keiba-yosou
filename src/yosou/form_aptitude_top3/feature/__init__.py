"""特徴量 68個を作る（設計書 09）。学習データも予測用データも、ここの同じクラスで作る（設計書 11 の 4）。

| 場所 | 中身 |
|---|---|
| ``feature_catalog.py`` | 特徴量 68個の一覧（名前・まとまり A〜I・数値かカテゴリか） |
| ``Feature``・``FeatureKind`` | 一覧の1行と、その型 |
| ``PredictionTiming`` | 予測する時点（木曜・前日・当日）と、時点ごとに使う特徴量 |
| ``EntryRecords`` | 特徴量を作る元の記録の入れ物 |
| ``FeatureBuilder`` | 入口。まとまりごとのクラスを順に呼んで、1つの表にする |
| ``group/`` | まとまり A〜I ごとに1クラス |
| ``history/`` | 過去の記録から数える部品（開催日より前のものだけを使う決まりを、ここで守る） |
"""

from .entry_columns import EntryColumns
from .entry_records import EntryRecords
from .feature_builder import FeatureBuilder
from .feature_catalog import CATEGORICAL_FEATURES, FEATURE_NAMES, FEATURES, categorical_columns_of
from .prediction_timing import PredictionTiming
from .time_windows import PEOPLE_WINDOW_DAYS, WORKOUT_WINDOW_DAYS

__all__ = [
    "FeatureBuilder", "EntryRecords", "EntryColumns", "PredictionTiming",
    "FEATURES", "FEATURE_NAMES", "CATEGORICAL_FEATURES", "categorical_columns_of",
    "WORKOUT_WINDOW_DAYS", "PEOPLE_WINDOW_DAYS",
]
