"""出走の行ごとに、開催日より前の記録を引く。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dated_records import DatedRecords

#: 突き合わせのために一時的に足す列の名前。
_ROW, _KEY, _DATE = "_row", "_key", "_date"


class AsOfLookup:
    """出走の行ごとに、過去の記録の表から「開催日の N 日前まで」で、いちばん新しい行を引く。

    例: 馬A が 6月1日に出走するなら、``days_before=1`` で、馬A の 5月31日までの記録のうち、いちばん新しい行。
    同じ日や、あとの日の記録は引かない（リークを防ぐ決まり。設計書 11 の 2）。
    """

    def __init__(self, entries: pd.DataFrame, entry_key: str) -> None:
        """``entry_key`` は、記録と突き合わせる鍵の列（``horse_id``・``jockey_code`` など）。"""
        self._entries = entries
        self._entry_key = entry_key

    def latest(self, records: DatedRecords, days_before: int) -> pd.DataFrame:
        """引いた行の表。行の並びと index は出走の行と同じで、当てはまる記録が無ければ欠損値。"""
        wanted = self._wanted_rows(days_before)
        candidates = self._candidate_rows(records)
        found = pd.merge_asof(wanted, candidates, on=_DATE, by=_KEY, direction="backward")
        in_entry_order = found.sort_values(_ROW).set_index(self._entries.index)
        return in_entry_order.drop(columns=[_ROW, _KEY, _DATE])

    def _wanted_rows(self, days_before: int) -> pd.DataFrame:
        """出走の行ごとの、鍵と「この日まで」の日付。``merge_asof`` のために日付の順に並べる。"""
        until = self._entries["race_date"] - pd.Timedelta(days=days_before)
        wanted = pd.DataFrame({
            _ROW: np.arange(len(self._entries)),
            _KEY: self._text_keys(self._entries[self._entry_key]),
            _DATE: until.astype("datetime64[ns]").to_numpy(),
        })
        return wanted.astype({_KEY: "str"}).sort_values(_DATE, kind="stable")

    def _candidate_rows(self, records: DatedRecords) -> pd.DataFrame:
        """記録の表に、突き合わせ用の鍵と日付の列を足して、日付の順に並べる。"""
        table = records.table
        candidates = table.assign(**{
            _KEY: self._text_keys(table[records.key_column]),
            _DATE: table[records.date_column].astype("datetime64[ns]").to_numpy(),
        })
        return candidates.astype({_KEY: "str"}).sort_values(_DATE, kind="stable")

    def _text_keys(self, values: pd.Series) -> np.ndarray:
        """鍵を文字列にそろえる（両側で型が違うと突き合わせられない）。欠損値は空文字。"""
        return values.astype("str").fillna("").to_numpy(dtype=object)
