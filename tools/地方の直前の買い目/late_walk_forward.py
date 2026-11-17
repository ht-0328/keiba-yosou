"""時間の順を守った確かめ: 区切りごとに、それより前のレースだけで学び直して、その区切りのレースに2つのモデルの値を付ける。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from .late_columns import RACE_DATE
from .late_models import LateModels

#: 最初の区切りの初めの日と、区切りの長さ（月）。最初の区切りより前のレースは、学ぶだけで当てない。
FIRST_START = "2024-07-01"
STEP_MONTHS = 3


@dataclass(frozen=True)
class LateWalkForward:
    """``fit`` は学ぶ関数（既定は ``LateModels.fit``。テストで差し替える）。"""

    first_start: str = FIRST_START
    step_months: int = STEP_MONTHS
    fit: Callable[[pd.DataFrame], LateModels] = LateModels.fit

    def run(self, rows: pd.DataFrame) -> pd.DataFrame:
        """``rows``（特徴量と答えの列のある表）のうち、最初の区切り以降の行に ``LIKENESS``・``PAYBACK`` を付けた表。"""
        last = rows[RACE_DATE].max()
        scored: list[pd.DataFrame] = []
        start = pd.Timestamp(self.first_start)
        while start <= last:
            end = start + pd.DateOffset(months=self.step_months)
            train = rows[rows[RACE_DATE] < start]
            test = rows[(rows[RACE_DATE] >= start) & (rows[RACE_DATE] < end)]
            if len(train) and len(test):
                scored.append(self.fit(train).score(test))
            start = end
        if not scored:
            raise ValueError(f"{self.first_start} 以降に、前の期間で学んで当てられるレースがありません")
        return pd.concat(scored, ignore_index=True)
