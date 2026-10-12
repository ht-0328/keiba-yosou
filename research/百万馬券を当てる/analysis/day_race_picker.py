"""第1段: 開催日ごとに、点数がいちばん高いレースを1つ選ぶ。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID


class DayRacePicker:
    """開催日ごとに、``score`` の列がいちばん高いレースを1つ選ぶ（1日1レースまで。docs/01 の 3）。

    点数が同じなら、レースIDの小さいほう（同じ日の早いレース）を取る。点数が欠損のレースは選ばない。
    """

    def __init__(self, score: str) -> None:
        self._score = score

    def pick(self, races: pd.DataFrame) -> pd.DataFrame:
        scored = races[races[self._score].notna()].sort_values([RACE_DATE, self._score, RACE_ID],
                                                               ascending=[True, False, True])
        return scored.drop_duplicates(RACE_DATE, keep="first").reset_index(drop=True)
