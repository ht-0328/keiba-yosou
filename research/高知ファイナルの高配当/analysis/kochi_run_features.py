"""高知の出走の行に、レースの前に分かる材料を付ける（ファイナルの印・近走・ファイナルの出走歴・同じ距離の出走歴・騎手・その日の傾向）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .day_trend import DayTrend
from .distance_history import DistanceHistory
from .final_history import FinalHistory
from .final_race import FINAL, FinalRace
from .jockey_form import JockeyForm
from .past_runs import PastRuns
from .relative_position import RelativePosition

_PLACED_FINISH = 3
#: 馬ごとに古い順に並べる鍵。
_ORDER = ["horse_id", "race_date", "race_no"]


@dataclass(frozen=True)
class KochiRunFeatures:
    """``runs``（``KochiRunsRepository`` の行）→ 材料の列が付いた、馬ごとに古い順の表。

    過去走は高知の行だけから作る。着順が付かなかった出走（競走中止など）は「3着以内でない」と数える。
    """

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        table = runs.copy()
        table["race_date"] = pd.to_datetime(table["race_date"])
        table = table.sort_values(_ORDER).reset_index(drop=True)
        table[FINAL] = FinalRace().mark(table)
        table["corner4_rel"] = RelativePosition().of(table["corner4"], table["field_size"])
        table["corner1_rel"] = RelativePosition().of(table["first_corner_rank"], table["field_size"])
        table["placed"] = self._flag(table["finish"] <= _PLACED_FINISH)
        table["won"] = self._flag(table["finish"] == 1)
        for step in (PastRuns(), FinalHistory(), DistanceHistory(), JockeyForm(), DayTrend()):
            table = step.add(table)
        return table

    def _flag(self, hit: pd.Series) -> pd.Series:
        """当たりなら 1.0、外れと着順なし（欠損値）は 0.0。"""
        return hit.fillna(False).astype(float)
