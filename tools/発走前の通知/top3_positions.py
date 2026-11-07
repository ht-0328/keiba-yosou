"""終わったレースの出走から、3着以内に来た馬の4コーナーの位置（前・中・後ろ）を数える。"""

from __future__ import annotations

import pandas as pd

from 発走前の通知.position_counts import PositionCounts

#: 位置（0 = 先頭、1 = 最後方）がこれより前なら「前」、後ろなら「後ろ」。頭数を3つに分ける。
FRONT_LINE, BACK_LINE = 1 / 3, 2 / 3


class Top3Positions:
    """位置 = （コーナーの順位 − 1）÷（そのレースでコーナーの順位がある頭数 − 1）。例: 12頭立ての4番手は 3/11 = 0.27 で「前」、
    9番手は 8/11 = 0.73 で「後ろ」。着順かコーナーの順位が1頭も無いレース（まだ終わっていない・直線のコース）は数えない。"""

    def count(self, runs: pd.DataFrame) -> PositionCounts:
        """``runs`` は ``VenueRunRepository`` の表（列 ``race_id``・``finish``・``corner``）。"""
        ran = runs[runs["corner"].notna()]
        field = ran.groupby("race_id")["corner"].transform("size")
        position = (ran["corner"] - 1) / (field - 1).where(field > 1)
        finished = ran.groupby("race_id")["finish"].transform(lambda finish: finish.notna().any())
        top3 = ran[finished & (ran["finish"] <= 3) & position.notna()]
        place = position[top3.index]
        return PositionCounts(races=int(top3["race_id"].nunique()), top3=len(top3), front=int((place < FRONT_LINE).sum()),
                              middle=int(((place >= FRONT_LINE) & (place <= BACK_LINE)).sum()), back=int((place > BACK_LINE).sum()))
