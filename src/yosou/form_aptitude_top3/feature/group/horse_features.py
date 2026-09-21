"""B. 馬のこと（9個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_columns import EntryColumns
from ..entry_records import EntryRecords

#: どれも事実表の列をそのまま使う（特徴量の名前 → 事実表の列）。
_COPIED = EntryColumns({
    "性別": "sex", "馬齢": "age", "所属": "affiliation", "枠番": "frame_no", "馬番": "horse_no",
    "斤量": "carried", "馬体重": "body_weight", "馬体重の増減": "weight_change", "ブリンカー": "blinker",
})


class HorseFeatures:
    """B. 馬のこと。今日の馬の条件と状態。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        return _COPIED.select(records.entries)
