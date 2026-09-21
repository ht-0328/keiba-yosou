"""A. レースの条件（9個）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通 import codes

from ..entry_columns import EntryColumns
from ..entry_records import EntryRecords
from ..value_types import as_numbers, as_yes_no

#: 事実表の列をそのまま使う特徴量（特徴量の名前 → 事実表の列）。
_COPIED = EntryColumns({
    "競馬場": "venue", "芝ダ": "surface", "コース": "course", "距離": "distance_m",
    "出走頭数": "field_size", "開催月": "month",
})
#: 馬場状態として使う値（良・稍重・重・不良）。事実表の「?」（未発表）は欠損値にする。
_KNOWN_GOINGS = frozenset(codes.TRACK_CONDITION.values())
#: 事実表のクラスの並び順のうち、付け直すもの（設計書 09 の A の ※）。
#: 格付けの無い重賞（14）は G3（8）と同じ位置に、条件不明（99）は欠損値にする。
_CLASS_ORDER_FIXES: dict[int, float] = {14: 8.0, 99: np.nan}


class RaceConditionFeatures:
    """A. レースの条件。同じレースの馬は、みな同じ値になる。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        going = entries["condition"]
        class_order = as_numbers(entries["class_order"])
        return _COPIED.select(entries).assign(**{
            "馬場状態": going.where(going.isin(_KNOWN_GOINGS)),
            "クラス": class_order.replace(_CLASS_ORDER_FIXES),
            "牡馬と牝馬が一緒に走るか": as_yes_no(entries["mixed_sex"]),
        })
