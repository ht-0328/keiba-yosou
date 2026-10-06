"""A. レースの条件（9個）。"""

from __future__ import annotations

from collections.abc import Mapping

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
#: 中央の事実表のクラスの並び順のうち、付け直すもの（設計書 09 の A の ※）。
#: 格付けの無い重賞（14）は G3（8）と同じ位置に、条件不明（99）は欠損値にする。
JRA_CLASS_ORDER_FIXES: dict[int, float] = {14: 8.0, 99: np.nan}
#: 地方の事実表のクラスの並び順の付け直し（地方の設計書 09 の A）。条件不明（99）だけを欠損値にする。
LOCAL_CLASS_ORDER_FIXES: dict[int, float] = {99: np.nan}


class RaceConditionFeatures:
    """A. レースの条件。同じレースの馬は、みな同じ値になる。

    ``class_order_fixes`` は、事実表のクラスの並び順のうち付け直すもの（並び順 → 付け直した値）。省略すると中央の決まり。
    """

    def __init__(self, class_order_fixes: Mapping[int, float] | None = None) -> None:
        self._class_order_fixes = dict(JRA_CLASS_ORDER_FIXES if class_order_fixes is None else class_order_fixes)

    def build(self, records: EntryRecords) -> pd.DataFrame:
        entries = records.entries
        going = entries["condition"]
        class_order = as_numbers(entries["class_order"])
        return _COPIED.select(entries).assign(**{
            "馬場状態": going.where(going.isin(_KNOWN_GOINGS)),
            "クラス": class_order.replace(self._class_order_fixes),
            "牡馬と牝馬が一緒に走るか": as_yes_no(entries["mixed_sex"]),
        })
