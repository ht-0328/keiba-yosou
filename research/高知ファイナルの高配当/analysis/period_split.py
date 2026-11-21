"""期間の分け方: 開催日を区切りの日で分け、期間ごとの名前（例 2016〜2019）を付ける。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class PeriodSplit:
    """``boundaries``（古い順の区切りの日）で分けた期間。区切りの日は後ろの期間に入る。"""

    boundaries: tuple[date, ...] = (date(2020, 1, 1), date(2024, 1, 1))

    def labels(self, days: pd.Series) -> pd.Series:
        """開催日の列 → 期間の名前の列。名前は、その期間に実際にある最初の年と最後の年。"""
        days = pd.to_datetime(days)
        position = pd.Series(0, index=days.index)
        for boundary in self.boundaries:
            position += (days >= pd.Timestamp(boundary)).astype(int)
        years = days.dt.year.groupby(position).agg(["min", "max"])
        names = {index: f"{row['min']}〜{row['max']}" for index, row in years.iterrows()}
        return position.map(names)
