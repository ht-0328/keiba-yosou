"""E. 近走のまとめ（10個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_columns import EntryColumns
from ..entry_records import EntryRecords
from ..history import AsOfLookup, DatedRecords, RecentRunSummary
from ..history.recent_run_summary import RUN_COUNT, SUMMARY_COLUMNS

#: 事実表と出走別着度数の列をそのまま使う特徴量（特徴量の名前 → 出走の記録の列）。
#: 通算の成績は出走別着度数から取るので、2023年より前の出走も含む。
_COPIED = EntryColumns({
    "推定脚質": "style_before", "通算の出走数": "ck_total_runs",
    "通算の勝利数": "ck_total_wins", "通算の3着以内の数": "ck_total_places",
})


class RecentFormFeatures:
    """E. 近走のまとめ。最近の調子（近5走）と、通算の成績。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        recent = self._recent_runs(records)
        run_count = recent[RUN_COUNT].fillna(0)
        features = pd.concat([_COPIED.select(entries), recent], axis=1)
        return features.assign(**{RUN_COUNT: run_count})

    def _recent_runs(self, records: EntryRecords) -> pd.DataFrame:
        """出走の行ごとの、開催日の前日までの新しい5走のまとめ。過去走が無ければ欠損値。"""
        summary = RecentRunSummary().build(records.past_runs)
        dated = DatedRecords(summary, key_column="horse_id", date_column="race_date")
        found = AsOfLookup(records.entries, "horse_id").latest(dated, days_before=1)
        return found[list(SUMMARY_COLUMNS)]
