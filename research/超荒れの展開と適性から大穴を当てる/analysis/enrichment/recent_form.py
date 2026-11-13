"""近走（2走前・3走前の着順と人気、前走のクラス）の列を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RecentForm:
    """出走の表（全部の過去走を含む。``horse_id``・``finish``・``popularity``・``class_name`` が要る）に、
    ``prev2_finish``・``prev2_popularity``・``prev3_finish``・``prev3_popularity``・``prev_class_name`` を足す
    （前走の着順と人気は事実表の ``prev_finish``・``prev_popularity`` を使う）。行の並びは馬・日付の順に変わる。"""

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.sort_values(["horse_id", "race_date", "race_id"], kind="stable").reset_index(drop=True)
        horse = frame.groupby("horse_id", sort=False)
        frame["prev_class_name"] = horse["class_name"].shift()
        for back in (2, 3):
            frame[f"prev{back}_finish"] = horse["finish"].shift(back)
            frame[f"prev{back}_popularity"] = horse["popularity"].shift(back)
        return frame
