"""成績を数える期間（探索・確認・参考・全期間）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Period:
    """年で区切った期間（両端を含む）。``last_year`` が None なら最後まで、``first_year`` が None なら最初から。"""

    label: str
    first_year: int | None
    last_year: int | None

    def contains(self, years: pd.Series) -> pd.Series:
        """``years``（整数の年）がこの期間に入るか。"""
        chosen = pd.Series(True, index=years.index)
        if self.first_year is not None:
            chosen &= years >= self.first_year
        if self.last_year is not None:
            chosen &= years <= self.last_year
        return chosen


#: 形を比べる期間（探索）と、探索で選んだものを一度だけ確かめる期間（確認）。当日の予測は 2015年からあるので、2015〜2018年は参考。
EXPLORE = Period("探索（2019〜2024年）", 2019, 2024)
CONFIRM = Period("確認（2025年〜）", 2025, None)
REFERENCE = Period("参考（2015〜2018年）", 2015, 2018)
WHOLE = Period("全期間", None, None)
PERIODS: tuple[Period, ...] = (EXPLORE, CONFIRM, REFERENCE, WHOLE)
