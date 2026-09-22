"""F. この条件での経験（10個）。"""

from __future__ import annotations

import pandas as pd

from ..entry_columns import EntryColumns
from ..entry_records import EntryRecords

#: どれも出走の記録の列をそのまま使う（特徴量の名前 → 出走の記録の列）。
#: ``ck_`` で始まる列は出走別着度数（2023年より前も含む通算）、それ以外は DB にある過去走（2023年以降）から数えたもの。
_COPIED = EntryColumns({
    "同じ競馬場・芝ダでの通算の出走数": "ck_venue_runs",
    "同じ競馬場・芝ダでの通算の3着以内の数": "ck_venue_places",
    "同じ芝ダ・距離帯での通算の出走数": "ck_band_runs",
    "同じ芝ダ・距離帯での通算の3着以内の数": "ck_band_places",
    "同じ芝ダ・馬場状態での通算の出走数": "ck_going_runs",
    "同じ芝ダ・馬場状態での通算の3着以内の数": "ck_going_places",
    "同じ競馬場・コース・距離での出走数": "course_runs_before",
    "同じ競馬場・コース・距離での3着以内の数": "course_places_before",
    "持ち時計のレース内順位（コース単位）": "best_time_unit_rank",
    "持ち時計のレース内順位（距離単位）": "best_time_dist_rank",
})


class AptitudeFeatures:
    """F. この条件での経験。同じコース・距離・馬場で走れるか。"""

    def build(self, records: EntryRecords) -> pd.DataFrame:
        return _COPIED.select(records.entries)
