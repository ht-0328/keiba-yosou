"""レース単位の特徴量のまとまりのクラスに共通の決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from .race_records import RaceRecords


class RaceFeatureGroup(Protocol):
    """レース単位の特徴量のまとまり1つ（荒れ具合の設計書 09 の A〜E）。1頭ごとの特徴量を集約して作る。"""

    def build(self, records: RaceRecords) -> pd.DataFrame:
        """列 = そのまとまりの特徴量。1行 = 1レースで、index はレースID。"""
        ...
