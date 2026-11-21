"""速さの指数（その日・その距離の全馬の時計の真ん中との差）と、その近走の材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .final_columns import SPEED_RANKED

#: その日・その距離の出走がこれより少ないと、真ん中の時計が当てにならないので指数を付けない。
MIN_RUNS = 16
#: 指数をそろえる距離（m）。
UNIT_DISTANCE = 1400


class SpeedForm:
    """``sp`` は走破タイムの指数（1400m あたりの秒。大きいほど速い）、``l3`` は上がり3ハロンの指数。
    ``mark`` は1走ごとの指数（高知の全部の走の表に付ける。その日・その距離の全馬がそろっていないと真ん中がずれる）、
    ``build`` は馬ごとの近走（今回より前の走だけ）とレースの中での順位・偏差。"""

    def mark(self, d: pd.DataFrame, eligible: pd.Series) -> pd.DataFrame:
        """``eligible`` の行（材料に使う走）だけで真ん中を取り、その行にだけ指数を付ける。"""
        d = d.copy()
        own = d[eligible]
        day = own.groupby(["race_date", "distance_m"])
        sp = (day["finish_time"].transform("median") - own["finish_time"]) / own["distance_m"] * UNIT_DISTANCE
        l3 = day["last3f"].transform("median") - own["last3f"]
        few = day["finish_time"].transform("size") < MIN_RUNS
        d["sp"] = sp.mask(few)
        d["l3"] = l3.mask(few)
        return d

    def build(self, d: pd.DataFrame) -> pd.DataFrame:
        d = d.sort_values(["horse_id", "race_date", "race_no"]).copy()
        horse = d.groupby("horse_id")
        for column in ("sp", "l3"):
            d[column + "_last"] = horse[column].shift(1)
            d[column + "_m3"] = horse[column].transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
            d[column + "_max5"] = horse[column].transform(lambda s: s.shift(1).rolling(5, min_periods=1).max())
        d["sp_trend"] = d["sp_last"] - d["sp_m3"]
        race = d.groupby("race_id")
        for column in SPEED_RANKED:
            d[column + "_rk"] = race[column].rank(ascending=False, method="average", na_option="keep")
            d[column + "_z"] = (d[column] - race[column].transform("mean")) / race[column].transform("std").replace(0, np.nan)
        return d
