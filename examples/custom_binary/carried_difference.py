"""特徴量追加の例。コピーして登録すると、依存項目を指定しなくても計算できる。"""

from collections.abc import Mapping

import pandas as pd

from yosou.shared.feature import EntryRecords, PredictionTiming
from yosou.shared.feature.feature_kind import FeatureKind


class CarriedDifference:
    name = "斤量とレース最小斤量との差"
    description = "同じレースの最も軽い斤量との差。人気で絞る前の全頭から計算。"
    kind = FeatureKind.NUMERIC
    known_from = PredictionTiming.THURSDAY
    dependencies = ("斤量",)

    def compute(self, records: EntryRecords, dependencies: Mapping[str, pd.Series]) -> pd.Series:
        carried = dependencies["斤量"]
        minimum = carried.groupby(records.entries["race_id"]).transform("min")
        return carried - minimum
