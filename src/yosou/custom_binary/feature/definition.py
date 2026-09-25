"""新しい特徴量が実装する決まり。計算に使う出走馬は人気で絞る前の全頭。"""

from collections.abc import Mapping
from typing import Protocol

import pandas as pd

from yosou.shared.feature import EntryRecords, PredictionTiming
from yosou.shared.feature.feature_kind import FeatureKind


class FeatureDefinition(Protocol):
    """``sources`` は省略できる。追加の元データ（``extra_data/extra_data_loader.py`` の ``SOURCES`` の名前）を使う特徴量だけ、
    ``sources = ("券種オッズ",)`` のように書く。その特徴量が選ばれたときだけ元データを読み、出走の行に列を足す。
    """

    name: str
    description: str
    kind: FeatureKind
    known_from: PredictionTiming
    dependencies: tuple[str, ...]

    def compute(self, records: EntryRecords, dependencies: Mapping[str, pd.Series]) -> pd.Series:
        """records.entries と同じインデックス・行順の1列を返す。"""
        ...
