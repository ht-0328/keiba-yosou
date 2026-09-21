"""特徴量のまとまり（A〜I）のクラスに共通の決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from .entry_records import EntryRecords


class FeatureGroup(Protocol):
    """特徴量のまとまり1つ（設計書 09 の A〜I）。記録から、そのまとまりの特徴量を作る。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        """列 = そのまとまりの特徴量。行の並びと index は ``records.entries`` と同じ。"""
        ...
