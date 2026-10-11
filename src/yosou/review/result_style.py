"""出走ごとの、結果の脚質（その走で実際に取った位置から）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.development_score import names as score_names
from yosou.development_score.pre_race_style import FRONT_LIMIT, MIDDLE_LIMIT
from yosou.shared.feature import as_numbers


class ResultStyle:
    """その走の最初のコーナーの位置で、逃げ（先頭）・先行（前から3分の1まで）・差し（3分の2まで）・追込に分ける。

    表 G（脚質 × ペース）を「結果のペースと位置」で引くときの脚質（設計書「買うレースと買い目を決める」08 の 3 の「展開が向かなかった」）。
    区切りは、レース前の脚質（``PreRaceStyle``）と同じ。最初のコーナーの記録が無い走は欠損値。
    """

    def of(self, runs: pd.DataFrame) -> pd.Series:
        rank, field_size = as_numbers(runs["first_corner_rank"]), as_numbers(runs["field_size"])
        position = ((rank - 1) / (field_size - 1)).where(field_size > 1)
        style = np.select([rank == 1, position <= FRONT_LIMIT, position <= MIDDLE_LIMIT, position > MIDDLE_LIMIT],
                          list(score_names.STYLES), default=None)
        return pd.Series(style, index=runs.index, dtype="object")
