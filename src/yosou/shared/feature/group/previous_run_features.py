"""D. 前走（11個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_columns import EntryColumns
from ..entry_records import EntryRecords
from ..value_types import as_numbers

#: 事実表の列をそのまま使う特徴量（特徴量の名前 → 事実表の列）。
_COPIED = EntryColumns({
    "前走の着順": "prev_finish", "前走の着差": "prev_time_diff", "前走の人気": "prev_popularity",
    "前走の上がり3F": "prev_last3f", "前走の上がり3Fのレース内順位": "prev_last3f_rank",
    "前走からの日数": "interval_days", "距離の変更": "distance_change",
    "芝ダ替わり": "surface_change", "クラスの変更": "class_change", "前走と同じ競馬場か": "venue_change",
})


class PreviousRunFeatures:
    """D. 前走。DB にある中央のレースのうち、今回より前でいちばん新しいもの。無ければ欠損値。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        corner_order = as_numbers(entries["prev_corner4"])
        field_size = as_numbers(entries["prev_field_size"])
        # 4コーナーの順位 ÷ 前走の頭数。0 に近いほど前
        return _COPIED.select(entries).assign(**{"前走の4コーナーの位置": corner_order / field_size})
