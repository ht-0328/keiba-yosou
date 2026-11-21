"""その日の傾向: その日の最終レースより前のレースだけから、3着以内の馬の位置・枠の平均と、騎手ごとのその日の成績。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

_DAY = "race_date"
_PLACED_FINISH = 3


@dataclass(frozen=True)
class DayTrend:
    """``runs`` は高知の出走の行（``race_date``・``race_no``・``finish``・``corner4_rel``・``frame_no``・``jockey_code``・``placed``・``won``）。

    付けた列はその日の全部の行に同じ値が入るが、使うのは最終レースの行だけ（最終レースより前の結果だけで出来ている）。
    """

    def add(self, runs: pd.DataFrame) -> pd.DataFrame:
        last_no = runs.groupby(_DAY)["race_no"].transform("max")
        earlier = runs[runs["race_no"] < last_no]
        placed = earlier[earlier["finish"] <= _PLACED_FINISH]
        day = placed.groupby(_DAY).agg(day_corner4_rel=("corner4_rel", "mean"), day_frame=("frame_no", "mean")).reset_index()
        jockey = earlier.groupby([_DAY, "jockey_code"]).agg(
            jockey_day_rides=("won", "size"), jockey_day_wins=("won", "sum"), jockey_day_places=("placed", "sum")).reset_index()
        return runs.merge(day, on=_DAY, how="left").merge(jockey, on=[_DAY, "jockey_code"], how="left")
