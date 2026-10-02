"""全レースのうち、何レースで買うことになるかを年ごとに数える。"""

from __future__ import annotations

import pandas as pd


class RaceParticipation:
    """年ごとの、予測したレースの数・買ったレースの数・その割合・1開催日あたりの買うレースの数。

    入力の列: rid・year・day（``evaluated`` は予測した全頭、``bought`` は買った馬券。1行 = 1点）。
    """

    def yearly(self, evaluated: pd.DataFrame, bought: pd.DataFrame) -> pd.DataFrame:
        races = evaluated.groupby("year")["rid"].nunique()
        days = evaluated.groupby("year")["day"].nunique()
        bought_races = bought.groupby("year")["rid"].nunique().reindex(races.index, fill_value=0)
        table = pd.DataFrame({
            "予測したレース": races,
            "買ったレース": bought_races,
            "買ったレースの割合": (bought_races / races).round(3),
            "1開催日あたりの買うレース": (bought_races / days).round(1),
        })
        return table.reset_index().rename(columns={"year": "年"})
