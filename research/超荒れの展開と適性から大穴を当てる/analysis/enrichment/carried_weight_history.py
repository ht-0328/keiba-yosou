"""斤量を、その馬の過去走と比べた列を足す（前走との増減と、同じ斤量・重い斤量での実績）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 「好走」とみなす着順。
PLACED = 3


@dataclass(frozen=True)
class CarriedWeightHistory:
    """出走の表（全部の過去走を含む。``horse_id``・``race_date``・``race_id``・``carried``・``finish`` が要る）に、
    今回より前の走だけから作った斤量の列を足す。行の並びは馬・日付の順に変わる。

    足す列:
    - ``prev_carried``・``carried_change``: 前走の斤量と、今回 − 前走（kg。正なら重くなった）
    - ``same_carried_runs``・``same_carried_places``: 今回と同じ斤量で走った回数と、そのうち3着以内の回数
    - ``heavier_places``: 今回より重い斤量で3着以内に入った回数（重い斤量で好走した力の裏付け）
    """

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.sort_values(["horse_id", "race_date", "race_id"], kind="stable").reset_index(drop=True)
        horse = frame.groupby("horse_id", sort=False)
        frame["prev_carried"] = horse["carried"].shift()
        frame["carried_change"] = frame["carried"] - frame["prev_carried"]
        placed = (frame["finish"] <= PLACED).astype(float)
        keys = [frame["horse_id"], frame["carried"]]
        frame["same_carried_runs"] = frame.groupby(keys, sort=False, dropna=False).cumcount().astype(float)
        frame["same_carried_places"] = placed.groupby(keys, sort=False, dropna=False).cumsum() - placed
        frame["heavier_places"] = self._heavier_places(frame, placed > 0)
        return frame

    @staticmethod
    def _heavier_places(frame: pd.DataFrame, placed: pd.Series) -> pd.Series:
        """各走に、同じ馬の3着以内の走を結び、今回より前で今回より重い斤量のものを数える。"""
        runs = frame[["horse_id", "race_date", "race_id", "carried"]].reset_index()
        good = frame.loc[placed, ["horse_id", "race_date", "race_id", "carried"]]
        good = good.rename(columns={"race_date": "good_date", "race_id": "good_race", "carried": "good_carried"})
        joined = runs.merge(good, on="horse_id")
        earlier = (joined["good_date"] < joined["race_date"]) | (
            (joined["good_date"] == joined["race_date"]) & (joined["good_race"] < joined["race_id"]))
        heavier = joined[earlier & (joined["good_carried"] > joined["carried"])]
        return heavier.groupby("index").size().reindex(frame.index, fill_value=0).astype(float)
