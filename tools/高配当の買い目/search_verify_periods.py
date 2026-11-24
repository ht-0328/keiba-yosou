"""買い目を、探す期間と確かめる期間に分ける。"""

from __future__ import annotations

import pandas as pd

from 高配当の買い目.pick_columns import RACE_DATE, SEARCH_LAST_YEAR


class SearchVerifyPeriods:
    """買い目の表（1行 = 1点）を、開催日の年で2つの期間に分ける。

    探す期間は ``search_last_year`` 年まで（この期間の成績を見て買い方を決めた）、確かめる期間はその次の年から（決めたあとの成績）。
    例: 既定（2022年）なら、2022年12月の買い目は探す期間、2023年1月の買い目は確かめる期間。
    """

    def __init__(self, search_last_year: int = SEARCH_LAST_YEAR) -> None:
        self._search_last_year = search_last_year

    @property
    def search_label(self) -> str:
        return f"探す期間（〜{self._search_last_year}年）"

    @property
    def verify_label(self) -> str:
        return f"確かめる期間（{self._search_last_year + 1}年〜）"

    def split(self, picks: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
        """（期間の名前, その期間の買い目）を、探す期間・確かめる期間の順に。"""
        searched = pd.to_datetime(picks[RACE_DATE]).dt.year <= self._search_last_year
        return [(self.search_label, picks[searched]), (self.verify_label, picks[~searched])]
