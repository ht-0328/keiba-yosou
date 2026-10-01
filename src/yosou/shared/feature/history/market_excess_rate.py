"""近1年の、市場に対する超過3着以内率。"""

from __future__ import annotations

import pandas as pd

from ..time_windows import PEOPLE_WINDOW_DAYS
from .as_of_lookup import AsOfLookup
from .dated_records import DatedRecords

#: 件数の少ない人の値を 0 に寄せる強さ（この出走数ぶん、超過 0 の出走を足したとみなす）。
SHRINK_STARTS = 50.0
#: 数える値の列（出走数・3着以内の数・オッズから見た3着以内率の和）。
_COUNTS = ["starts", "placed", "expected"]


class MarketExcessRate:
    """出走の行ごとに、その騎手（調教師・血統）の、開催日の前日までの 365日の「市場に対する超過3着以内率」を出す。

    超過 = (3着以内の数 − オッズから見た3着以内率の和) ÷ (出走数 + 50)。
    オッズが期待したより多く3着以内に来ていれば正、少なければ負。強い馬に乗っているだけの騎手は、期待も高いので
    超過は大きくならない。出走数が少ないと 0 に近づき、期間に出走が無ければ 0。鍵の無い出走の行は欠損値。

    例: 1年に 150回乗り、3着以内が 45回、オッズから見た3着以内率の和が 40 の騎手は、(45 − 40) ÷ (150 + 50) = 0.025。
    ``entry_key`` は出走の行の側の鍵の列で、過去の出走の表（``runs``）の側も同じ名前の列で突き合わせる。
    """

    def __init__(self, entries: pd.DataFrame, entry_key: str) -> None:
        self._entries = entries
        self._key = entry_key
        self._lookup = AsOfLookup(entries, entry_key)

    def of(self, runs: pd.DataFrame) -> pd.Series:
        """``runs`` は過去の出走（1行 = 1頭）で、鍵の列・``race_date``・``placed``（3着以内なら 1）・``expected``
        （オッズから見た3着以内率）を持つ。行の並びと index は出走の行と同じ。"""
        totals = DatedRecords(self._running_totals(runs), self._key, "race_date")
        until_yesterday = self._lookup.latest(totals, days_before=1).fillna(0.0)
        before_window = self._lookup.latest(totals, days_before=PEOPLE_WINDOW_DAYS + 1).fillna(0.0)
        starts = until_yesterday["starts"] - before_window["starts"]
        placed = until_yesterday["placed"] - before_window["placed"]
        expected = until_yesterday["expected"] - before_window["expected"]
        rate = (placed - expected) / (starts + SHRINK_STARTS)
        return rate.where(self._entries[self._key].notna())

    def _running_totals(self, runs: pd.DataFrame) -> pd.DataFrame:
        """鍵ごとの、その日までの出走数・3着以内の数・オッズから見た3着以内率の和の累計。"""
        days = runs.dropna(subset=[self._key]).groupby([self._key, "race_date"], as_index=False).agg(
            starts=("placed", "size"), placed=("placed", "sum"), expected=("expected", "sum"))
        ordered = days.sort_values([self._key, "race_date"], kind="stable").reset_index(drop=True)
        totals = ordered.groupby(self._key, sort=False)[_COUNTS].cumsum()
        return totals.assign(**{self._key: ordered[self._key], "race_date": ordered["race_date"]})
