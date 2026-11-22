"""レースの中での比べ（材料の順位と偏差）と、単勝オッズから作る材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .final_columns import MARKET_SHARE, POPULARITY_NOW, RANKED


class RaceRelative:
    """``ranks`` は ``RANKED`` の列に、レースの中での順位（``_rk``）と偏差（``_z``）を付ける。
    ``market`` は単勝オッズ（``win_odds``。学ぶときは確定、予想するときは発走前の断面）から、オッズが示す1着の確率 ``mkt``・その対数 ``lm``・
    その時点の人気 ``pop_now``（同じオッズは馬の並び順）・1番人気との対数の差 ``lm_gap``・近走の人気との差 ``pop_gap`` を付ける。"""

    def ranks(self, d: pd.DataFrame) -> pd.DataFrame:
        d = d.copy()
        race = d.groupby("race_id")
        for column in RANKED:
            d[column + "_rk"] = race[column].rank(method="average", na_option="keep")
            d[column + "_z"] = (d[column] - race[column].transform("mean")) / race[column].transform("std").replace(0, np.nan)
        return d

    def market(self, d: pd.DataFrame) -> pd.DataFrame:
        d = d.sort_values(["horse_id", "race_date", "race_no"]).copy()
        share = 1 / d["win_odds"]
        d[MARKET_SHARE] = share / share.groupby(d["race_id"]).transform("sum")
        d["lm"] = np.log(d[MARKET_SHARE])
        race = d.groupby("race_id")
        d[POPULARITY_NOW] = race["win_odds"].rank(method="first")
        d["lm_gap"] = d["lm"] - race["lm"].transform("max")
        d["pop_gap"] = d["pop_m3"] - d[POPULARITY_NOW]
        return d
