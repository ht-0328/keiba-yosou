"""騎手の、直近365日の高知の成績（その日より前だけ）。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

WINDOW = "365D"


class JockeyForm:
    """``j_n`` 騎乗数・``j_win`` 勝率・``j_top3`` 3着以内率・``j_c4`` 4コーナーの位置の平均・``j_lift`` 3着以内の数 ÷ 人気から見込まれる数。
    ``popularity_rates`` は 単勝人気 → 3着以内率（``j_lift`` の見込みに使う）。学んだときの値をモデルと一緒に保存し、予想でも同じ値を使う。"""

    def rates(self, d: pd.DataFrame) -> dict[float, float]:
        """表の全部の走から数えた、単勝人気ごとの 3着以内率。"""
        return {float(popularity): float(rate) for popularity, rate in d.groupby("popularity")["top3"].mean().items()}

    def build(self, d: pd.DataFrame, popularity_rates: Mapping[float, float]) -> pd.DataFrame:
        rides = d[["jockey_code", "race_date", "win", "top3", "c4rel"]].copy()
        rides["expected"] = d["popularity"].map(dict(popularity_rates))
        days = rides.groupby(["jockey_code", "race_date"]).agg(n=("win", "size"), w=("win", "sum"), t=("top3", "sum"), c=("c4rel", "sum"),
                                                              e=("expected", "sum")).reset_index()
        parts = []
        for code, own in days.groupby("jockey_code"):
            own = own.set_index("race_date").sort_index()
            past = own[["n", "w", "t", "c", "e"]].rolling(WINDOW, closed="left").sum()
            parts.append(pd.DataFrame({"jockey_code": code, "race_date": own.index, "j_n": past["n"].values, "j_win": (past["w"] / past["n"]).values,
                                       "j_top3": (past["t"] / past["n"]).values, "j_c4": (past["c"] / past["n"]).values,
                                       "j_lift": (past["t"] / past["e"]).values}))
        return d.merge(pd.concat(parts), on=["jockey_code", "race_date"], how="left")
