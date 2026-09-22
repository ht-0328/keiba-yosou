"""過去走を、馬ごとの「その走までの近5走のまとめ」にする。"""

from __future__ import annotations

import pandas as pd

from ..value_types import as_numbers

#: 近走として数える走数。
RECENT_RUNS = 5
#: まとめの列の名前（そのまま特徴量の名前になる）。
RUN_COUNT = "近5走の数"
SUMMARY_COLUMNS: tuple[str, ...] = (
    RUN_COUNT, "近5走の平均着順", "近5走の最高着順", "近5走の平均着差",
    "近5走の平均上がり順位", "近5走の平均4コーナー位置",
)


class RecentRunSummary:
    """過去走の表（1行 = 1走）に、その走を含めた新しい5走のまとめを付ける。

    5走に満たなければ、ある分だけで計算する。着順の無い走（競走中止など）は、平均から外れる。
    """

    def build(self, past_runs: pd.DataFrame) -> pd.DataFrame:
        """列は ``horse_id``・``race_date`` と ``SUMMARY_COLUMNS``。馬・開催日の古い順に並べる。"""
        runs = past_runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        runs = runs.reset_index(drop=True)
        horse = runs["horse_id"]
        measures = self._measures(runs)
        recent = measures.groupby(horse, sort=False).rolling(RECENT_RUNS, min_periods=1)
        means = recent.mean().reset_index(level=0, drop=True)
        best_finish = recent["finish"].min().reset_index(level=0, drop=True)
        run_number = runs.groupby("horse_id", sort=False).cumcount() + 1
        return pd.DataFrame({
            "horse_id": horse,
            "race_date": runs["race_date"],
            RUN_COUNT: run_number.clip(upper=RECENT_RUNS),
            "近5走の平均着順": means["finish"],
            "近5走の最高着順": best_finish,
            "近5走の平均着差": means["time_diff"],
            "近5走の平均上がり順位": means["last3f_rank"],
            "近5走の平均4コーナー位置": means["corner_position"],
        })

    def _measures(self, runs: pd.DataFrame) -> pd.DataFrame:
        """平均を取る値。4コーナーの位置は、4コーナーの順位 ÷ 頭数（0 に近いほど前）。"""
        return pd.DataFrame({
            "finish": as_numbers(runs["finish"]),
            "time_diff": as_numbers(runs["time_diff"]),
            "last3f_rank": as_numbers(runs["last3f_rank"]),
            "corner_position": as_numbers(runs["corner4"]) / as_numbers(runs["field_size"]),
        })
