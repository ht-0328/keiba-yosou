"""馬ごとの近走の材料（位置・着差・着順・人気・上がり・ファイナルレースの成績・同じ距離の成績）。今回より前の走だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class HorseForm:
    """``RunBase`` の表（馬 → 開催日 → レース番号の順）に列を足す。どの列も、その行より前の走だけから作る。"""

    def build(self, d: pd.DataFrame) -> pd.DataFrame:
        d = d.copy()
        horse = d.groupby("horse_id")
        for runs in (3, 5):
            d[f"c4rel_m{runs}"] = self._roll(horse, "c4rel", runs, "mean")
            d[f"c1rel_m{runs}"] = self._roll(horse, "c1rel", runs, "mean")
            d[f"td_m{runs}"] = self._roll(horse, "time_diff", runs, "mean")
            d[f"td_min{runs}"] = self._roll(horse, "time_diff", runs, "min")
            d[f"top3_s{runs}"] = self._roll(horse, "top3", runs, "sum")
            d[f"pop_m{runs}"] = self._roll(horse, "popularity", runs, "mean")
            d[f"fin_m{runs}"] = self._roll(horse, "finish", runs, "mean")
        d["c4rel_min5"] = self._roll(horse, "c4rel", 5, "min")
        d["l3rank_m5"] = self._roll(horse, "last3f_rank", 5, "mean")
        d["l3rank_min5"] = self._roll(horse, "last3f_rank", 5, "min")
        d["prev_final"] = horse["final"].shift(1)
        d["prev_l3rank"] = horse["last3f_rank"].shift(1)
        d["prev_dist"] = horse["distance_m"].shift(1)
        d["prev_class"] = horse["class_order"].shift(1)
        d["prev_carried"] = horse["carried"].shift(1)
        d["fin_f"] = d["final"].astype(float)
        d["f_top3"] = d["top3"] * d["fin_f"]
        d["f_win"] = d["win"] * d["fin_f"]
        horse = d.groupby("horse_id")
        d["f_runs"] = self._before(horse, "fin_f")
        d["f_places"] = self._before(horse, "f_top3")
        d["f_wins"] = self._before(horse, "f_win")
        same_distance = d.groupby(["horse_id", "distance_m"])
        d["d_runs"] = same_distance.cumcount()
        d["d_places"] = self._before(same_distance, "top3")
        d["d_td_m"] = same_distance["time_diff"].transform(lambda s: s.shift(1).expanding().mean())
        return d

    def derived(self, d: pd.DataFrame) -> pd.DataFrame:
        """前走との差・率など、上の列から決まる列。"""
        d = d.copy()
        d["is_final"] = d["final"].astype(int)
        d["female"] = (d["sex"] == "牝").astype(int)
        d["f_rate"] = d["f_places"] / d["f_runs"].replace(0, np.nan)
        d["d_rate"] = d["d_places"] / d["d_runs"].replace(0, np.nan)
        d["prev_is_final"] = (d["prev_final"] == True).astype(int)  # noqa: E712 — 前走が無い行は欠損値なので、真とだけ比べる
        d["dist_diff"] = d["distance_m"] - d["prev_dist"]
        d["class_diff"] = d["prev_class"] - d["class_order"]
        d["carried_diff"] = d["carried"] - d["prev_carried"]
        d["jchg"] = (d["jockey_change"].astype(str) == "乗り替わり").astype(int)
        return d

    @staticmethod
    def _roll(horse, column: str, runs: int, how: str) -> pd.Series:
        return horse[column].transform(lambda s: getattr(s.shift(1).rolling(runs, min_periods=1), how)())

    @staticmethod
    def _before(group, column: str) -> pd.Series:
        return group[column].transform(lambda s: s.shift(1).cumsum()).fillna(0)
