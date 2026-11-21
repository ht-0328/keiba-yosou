"""調教師の、直近365日・30日の高知の成績（その日より前）と、その日のそのレースより前の成績。"""

from __future__ import annotations

import pandas as pd


class TrainerForm:
    """``t_n``・``t_win``・``t_top3`` は直近365日の出走数・勝率・3着以内率、``t_n30``・``t_top3_30`` は直近30日、
    ``t_form`` は 30日の3着以内率 − 365日の3着以内率（最近の調子）。``tday_*`` はその日のそのレースより前の勝利数・3着以内の数・出走数。"""

    def build(self, d: pd.DataFrame) -> pd.DataFrame:
        d = d.merge(self._windows(d), on=["trainer_code", "race_date"], how="left")
        d = d.merge(self._same_day(d), on=["race_date", "trainer_code", "race_no"], how="left")
        d["t_form"] = d["t_top3_30"] - d["t_top3"]
        return d

    @staticmethod
    def _windows(d: pd.DataFrame) -> pd.DataFrame:
        days = d.groupby(["trainer_code", "race_date"]).agg(n=("win", "size"), w=("win", "sum"), p=("top3", "sum")).reset_index()
        parts = []
        for code, own in days.groupby("trainer_code"):
            own = own.set_index("race_date").sort_index()
            year = own[["n", "w", "p"]].rolling("365D", closed="left").sum()
            month = own[["n", "p"]].rolling("30D", closed="left").sum()
            parts.append(pd.DataFrame({"trainer_code": code, "race_date": own.index, "t_n": year["n"].values, "t_win": (year["w"] / year["n"]).values,
                                       "t_top3": (year["p"] / year["n"]).values, "t_top3_30": (month["p"] / month["n"]).values,
                                       "t_n30": month["n"].values}))
        return pd.concat(parts)

    @staticmethod
    def _same_day(d: pd.DataFrame) -> pd.DataFrame:
        t = d.groupby(["race_date", "trainer_code", "race_no"]).agg(a=("win", "sum"), b=("top3", "sum"), c=("win", "size")).reset_index()
        t = t.sort_values(["race_date", "trainer_code", "race_no"])
        day = t.groupby(["race_date", "trainer_code"])
        t["tday_win"] = day["a"].cumsum() - t["a"]
        t["tday_top3"] = day["b"].cumsum() - t["b"]
        t["tday_n"] = day["c"].cumsum() - t["c"]
        return t[["race_date", "trainer_code", "race_no", "tday_win", "tday_top3", "tday_n"]]
