"""セルごとに、決着の型（◎ の着順・3着以内の馬の印と位置・◎○▲ で決まった割合）を数える。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .grades_table import CELL
from .horse_slots import POSITION

#: 表の列。
COLUMNS: tuple[str, ...] = ("セル", "レース", "◎1着", "◎2着", "◎3着", "◎4着以下", "◎○▲で決着", "◎○▲が2頭以上", "◎が3着以内",
                            "3着以内の印: ◎", "○", "▲", "△", "☆", "注", "消", "無印", "3着以内の位置の平均", "3着以内が位置4以下")


class CasesReport:
    """印を付けた表（1行 = 1頭。列 race_id・mark・finish・probability）と馬の位置（``HorseSlots``）とセル（``GradesTable``）から、
    セルごとの決着の型の表を作る（docs/01 の 3）。

    ◎ の着順の分布、3着以内の3頭が ◎○▲ だけだった割合（◎○▲で決着）・◎○▲ が2頭以上入った割合・◎ が3着以内に来た割合、
    3着以内に来た馬の印の内訳（レースあたりの頭数）、3着以内の馬の位置（◎ を 0、ほかは確率の順）の平均と、位置が 4 以下（○▲△ より下）の馬の割合。
    型の候補を絞るためではなく、型が決着の型に合っているかを読むための表。
    """

    def table(self, marked: pd.DataFrame, slots: pd.DataFrame, grades: pd.DataFrame) -> pd.DataFrame:
        horses = marked[["race_id", "horse_no", "mark", "finish"]].assign(race_id=lambda frame: frame["race_id"].astype(str),
                                                                        horse_no=lambda frame: frame["horse_no"].astype(int))
        horses = horses.merge(slots[["race_id", "horse_no", POSITION]], on=["race_id", "horse_no"], how="left")
        horses = horses.merge(grades[["race_id", CELL]].assign(race_id=lambda frame: frame["race_id"].astype(str)), on="race_id", how="inner")
        rows = [self._row(cell, group) for cell, group in horses.groupby(CELL, sort=True)]
        rows.append(self._row("全部", horses))
        return pd.DataFrame(rows, columns=list(COLUMNS))

    @staticmethod
    def _row(cell: str, horses: pd.DataFrame) -> dict[str, object]:
        races = horses["race_id"].nunique()
        tops = horses[horses["mark"] == "◎"]
        top_finish = tops["finish"].fillna(99)
        placed = horses[horses["finish"] <= 3]
        top_marks = placed.groupby("race_id")["mark"].apply(lambda marks: int(marks.isin(["◎", "○", "▲"]).sum()))
        counts = placed["mark"].value_counts()
        positions = placed[POSITION]
        return {
            "セル": cell, "レース": races,
            "◎1着": (top_finish == 1).sum() / races, "◎2着": (top_finish == 2).sum() / races, "◎3着": (top_finish == 3).sum() / races,
            "◎4着以下": (top_finish > 3).sum() / races,
            "◎○▲で決着": (top_marks >= 3).sum() / races, "◎○▲が2頭以上": (top_marks >= 2).sum() / races, "◎が3着以内": (top_finish <= 3).sum() / races,
            "3着以内の印: ◎": counts.get("◎", 0) / races, "○": counts.get("○", 0) / races, "▲": counts.get("▲", 0) / races, "△": counts.get("△", 0) / races,
            "☆": counts.get("☆", 0) / races, "注": counts.get("注", 0) / races, "消": counts.get("消", 0) / races, "無印": counts.get("－", 0) / races,
            "3着以内の位置の平均": float(np.nanmean(positions)) if positions.notna().any() else np.nan,
            "3着以内が位置4以下": float((positions >= 4).sum() / len(placed)) if len(placed) else np.nan,
        }
