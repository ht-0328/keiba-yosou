"""J. 人気と人気の履歴（4個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import EntryRecords, as_numbers
from yosou.shared.feature.history import AsOfLookup, DatedRecords

from .history import SUMMARY_COLUMNS, PopularityRunSummary

#: 出走の行からそのまま作る特徴量の名前。
POPULARITY_RANK = "人気順位"
PREV_POPULARITY_GAP = "前走の人気と着順の差"


class PopularityHistoryFeatures:
    """J. 人気と人気の履歴（設計書 09 の J）。``FeatureGroup`` を守る。

    「今回どれだけ人気か」と、「これまで人気どおりに走ってきたか」を表す。決定木は2つの列を引き算して
    比べられないので、着順と人気の差は、あらかじめ列にしておく。
    """

    def build(self, records: EntryRecords) -> pd.DataFrame:
        return pd.concat([self._this_run(records.entries), self._recent_runs(records)], axis=1)

    def _this_run(self, entries: pd.DataFrame) -> pd.DataFrame:
        """今回の人気と、前走の人気と着順の差。前走の着順か人気が無ければ、差は欠損値。"""
        prev_finish = as_numbers(entries["prev_finish"])
        prev_popularity = as_numbers(entries["prev_popularity"])
        return pd.DataFrame({
            POPULARITY_RANK: as_numbers(entries["popularity"]),
            PREV_POPULARITY_GAP: prev_finish - prev_popularity,
        }, index=entries.index)

    def _recent_runs(self, records: EntryRecords) -> pd.DataFrame:
        """出走の行ごとの、開催日の前日までの新しい5走の人気のまとめ。過去走が無ければ欠損値。"""
        summary = PopularityRunSummary().build(records.past_runs)
        dated = DatedRecords(summary, key_column="horse_id", date_column="race_date")
        found = AsOfLookup(records.entries, "horse_id").latest(dated, days_before=1)
        return found[list(SUMMARY_COLUMNS)]
