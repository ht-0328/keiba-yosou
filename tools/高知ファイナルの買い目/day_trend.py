"""その日の、そのレースより前のレースだけから作る材料（3着以内に来た馬の位置・枠・人気、騎手のその日の成績）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

_SUMS: tuple[str, ...] = ("s_c4", "s_c1", "s_frame", "s_pop", "n", "w_c4", "w_fav")
_OUTPUT: tuple[str, ...] = ("day_races", "day_c4", "day_c1", "day_frame", "day_pop", "day_win_c4", "day_fav_win")


class DayTrend:
    """ファイナルレースはその日のいちばん後ろなので、その日の前のレース全部の結果を使える。
    ``day_races`` はその日の、結果の出ている前のレースの数。``bias_fit`` は 自分のいつもの4コーナーの位置と、その日に来ている位置の近さ。
    ``frame_fit`` は枠の近さ。"""

    def build(self, d: pd.DataFrame) -> pd.DataFrame:
        d = d.merge(self._races(d), on=["race_date", "race_no"], how="left")
        d = d.merge(self._jockeys(d), on=["race_date", "jockey_code", "race_no"], how="left")
        d["bias_fit"] = -(d["c4rel_m3"] - d["day_c4"]).abs()
        d["frame_fit"] = -(d["frame_no"] - d["day_frame"]).abs()
        return d

    @staticmethod
    def _races(d: pd.DataFrame) -> pd.DataFrame:
        """レースごとの、そのレースより前の集計。これから走るレース（3着以内の馬がまだいない）にも行を作る。"""
        placed = d[d["finish"] <= 3].groupby(["race_date", "race_no"]).agg(
            s_c4=("c4rel", "sum"), s_c1=("c1rel", "sum"), s_frame=("frame_no", "sum"), s_pop=("popularity", "sum"), n=("c4rel", "size")).reset_index()
        winners = d[d["finish"] == 1].groupby(["race_date", "race_no"]).agg(
            w_c4=("c4rel", "sum"), w_fav=("popularity", lambda s: float((s == 1).sum()))).reset_index()
        r = d[["race_date", "race_no"]].drop_duplicates()
        r = r.merge(placed, on=["race_date", "race_no"], how="left").merge(winners, on=["race_date", "race_no"], how="left").fillna(0)
        r = r.sort_values(["race_date", "race_no"])
        day = r.groupby("race_date")
        for column in _SUMS:
            r["c_" + column] = day[column].cumsum() - r[column]
        finished = (r["n"] > 0).astype(float)
        r["day_races"] = finished.groupby(r["race_date"]).cumsum() - finished
        heads = r["c_n"].replace(0, np.nan)
        races = r["day_races"].replace(0, np.nan)
        r["day_c4"] = r["c_s_c4"] / heads
        r["day_c1"] = r["c_s_c1"] / heads
        r["day_frame"] = r["c_s_frame"] / heads
        r["day_pop"] = r["c_s_pop"] / heads
        r["day_win_c4"] = r["c_w_c4"] / races
        r["day_fav_win"] = r["c_w_fav"] / races
        return r[["race_date", "race_no", *_OUTPUT]]

    @staticmethod
    def _jockeys(d: pd.DataFrame) -> pd.DataFrame:
        j = d.groupby(["race_date", "jockey_code", "race_no"]).agg(jw=("win", "sum"), jt=("top3", "sum"), jn=("win", "size")).reset_index()
        j = j.sort_values(["race_date", "jockey_code", "race_no"])
        day = j.groupby(["race_date", "jockey_code"])
        for source, name in (("jw", "jday_win"), ("jt", "jday_top3"), ("jn", "jday_n")):
            j[name] = day[source].cumsum() - j[source]
        return j[["race_date", "jockey_code", "race_no", "jday_win", "jday_top3", "jday_n"]]
