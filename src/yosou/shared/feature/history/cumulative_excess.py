"""鍵ごとの、開催日の前日までの全期間の「当たりの数」と「オッズから見た期待の和」の累計。"""

from __future__ import annotations

import pandas as pd

from .as_of_lookup import AsOfLookup
from .dated_records import DatedRecords

#: 数える値の列（出走数・当たりの数・オッズから見た期待の和）。
COUNTS: tuple[str, ...] = ("starts", "hits", "expected")


class CumulativeExcess:
    """出走の行ごとに、その鍵（コース×距離の変更 など）の、開催日の前日までの全期間の累計を引く。

    市場に対する超過の率（(当たりの数 − 期待の和) ÷ (出走数 + 縮める強さ)）を作るための数。``MarketExcessRate`` は
    近1年の窓で数えるが、こちらは窓を切らない（コースの傾向は出走が少なく、全期間を使いたいため）。
    同じ日や、あとの日の出走は数えない（設計書 11 の 2）。期間に出走が無ければ 0。
    """

    def __init__(self, entries: pd.DataFrame, entry_key: str) -> None:
        """``entry_key`` は出走の行の側の鍵の列。過去の出走の側も同じ名前の列で突き合わせる。"""
        self._key = entry_key
        self._lookup = AsOfLookup(entries, entry_key)

    def totals(self, runs: pd.DataFrame, hit_column: str, expected_column: str) -> pd.DataFrame:
        """列は ``COUNTS``。行の並びと index は出走の行と同じ。

        ``runs`` は過去の出走（1行 = 1頭）で、鍵の列・``race_date``・当たりの列（1 か 0）・期待の列を持つ。
        """
        days = runs.dropna(subset=[self._key]).groupby([self._key, "race_date"], as_index=False).agg(
            starts=(hit_column, "size"), hits=(hit_column, "sum"), expected=(expected_column, "sum"))
        ordered = days.sort_values([self._key, "race_date"], kind="stable").reset_index(drop=True)
        running = ordered.groupby(self._key, sort=False)[list(COUNTS)].cumsum()
        totals = running.assign(**{self._key: ordered[self._key], "race_date": ordered["race_date"]})
        return self._lookup.latest(DatedRecords(totals, self._key, "race_date"), days_before=1)[list(COUNTS)].fillna(0.0)
