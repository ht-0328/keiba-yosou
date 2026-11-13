"""レースの結果側の様子（ペース・勝ち馬と2着の差・1番人気の着順）の列を足す。理解のための表にだけ使い、手がかりには使わない。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class RaceOutcomeSide:
    """出走の表に次の列を足す（どれもレースが終わってから分かる値）。

    - ``pace_gap``: 前半3ハロン − 後半3ハロン（秒）を、同じ競馬場・芝ダ・距離のレースの中央値との差にしたもの。負ほど前半が速い（ハイペース）
    - ``second_gap``: 2着の馬のタイム差（秒。勝ち馬が2着をどれだけ離したか）
    - ``favorite_finish``: 1番人気の確定着順
    """

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.copy()
        pace = frame["first3f"] - frame["last3f_race"]
        races = frame.assign(pace=pace).drop_duplicates("race_id")
        median = races.groupby(["venue", "surface", "distance_m"])["pace"].median().rename("pace_median")
        frame = frame.merge(median, on=["venue", "surface", "distance_m"], how="left")
        frame["pace_gap"] = (frame["first3f"] - frame["last3f_race"]) - frame["pace_median"]
        second = frame.loc[frame["finish"] == 2].drop_duplicates("race_id").set_index("race_id")["time_diff"]
        favorite = frame.loc[frame["popularity"] == 1].drop_duplicates("race_id").set_index("race_id")["finish"]
        frame["second_gap"] = frame["race_id"].map(second)
        frame["favorite_finish"] = frame["race_id"].map(favorite)
        return frame.drop(columns="pace_median")
