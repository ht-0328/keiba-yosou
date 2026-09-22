"""血統の産駒の、近1年の3着以内の割合。"""

from __future__ import annotations

import pandas as pd

from .top3_rate import Top3Rate

#: 血統の名前（と芝ダ）をつないだ、突き合わせの鍵を入れる列。
_KEY_COLUMN = "_pedigree_key"
#: 血統の名前と芝ダをつなぐ文字。
_SEPARATOR = "／"


class PedigreeTop3Rate:
    """出走の行ごとに、その馬の父（か母父）の産駒の、開催日の前日までの 365日の3着以内の割合を出す。

    **産駒の成績なので、種牡馬自身が現役だったころの成績ではない。**
    芝ダを問わない割合が「血統の力」、そのレースと同じ芝ダだけの割合が「血統の芝ダ適性」になる。
    """

    def __init__(self, entries: pd.DataFrame, name_column: str) -> None:
        """``name_column`` は出走の行の ``sire``（父）か ``damsire``（母父）。"""
        self._entries = entries
        self._name_column = name_column

    def of_all_surfaces(self, pedigree_days: pd.DataFrame) -> pd.Series:
        """芝ダを問わない割合（血統の力）。"""
        days = pedigree_days.groupby(["pedigree_name", "race_date"], as_index=False)[["starts", "places"]].sum()
        return self._rate(self._entries[self._name_column], days["pedigree_name"], days)

    def of_same_surface(self, pedigree_days: pd.DataFrame) -> pd.Series:
        """そのレースと同じ芝ダだけの割合（血統の芝ダ適性）。"""
        entry_keys = self._joined(self._entries[self._name_column], self._entries["surface"])
        history_keys = self._joined(pedigree_days["pedigree_name"], pedigree_days["surface"])
        return self._rate(entry_keys, history_keys, pedigree_days)

    def _rate(self, entry_keys: pd.Series, history_keys: pd.Series, days: pd.DataFrame) -> pd.Series:
        entries = self._entries.assign(**{_KEY_COLUMN: entry_keys})
        history = days.assign(**{_KEY_COLUMN: history_keys})
        return Top3Rate(entries, _KEY_COLUMN, _KEY_COLUMN).of(history)

    def _joined(self, names: pd.Series, surfaces: pd.Series) -> pd.Series:
        """血統の名前と芝ダをつないだ鍵。どちらかが欠けていれば欠損値（突き合わない）。"""
        return names.astype("str") + _SEPARATOR + surfaces.astype("str")
