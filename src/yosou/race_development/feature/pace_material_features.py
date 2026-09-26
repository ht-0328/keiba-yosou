"""P. ペースの材料（10個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import RaceRecords, as_numbers

from .race_order_statistic import RaceOrderStatistic

#: 「前に行きたい馬」とみなす先団率の線（設計書 09 の P）。
FRONT_RATE_LINE = 0.5
#: 前にいる馬として平均する頭数。
_FRONT_RUNNERS = 3


class PaceMaterialFeatures:
    """P. 先行しそうな馬が何頭いて、どれだけ競り合いそうか（設計書 09 の P）。``RaceFeatureGroup`` を守る。

    1頭ごとの K・L をレースに1つの値に集約する。
    """

    def __init__(self) -> None:
        self._order = RaceOrderStatistic()

    def build(self, records: RaceRecords) -> pd.DataFrame:
        features, race = records.horse_features, records.entries["race_id"]
        lead = as_numbers(features["先頭率"])
        front = as_numbers(features["先団率"])
        by_race = race.groupby(race, sort=False)
        top = lead.groupby(race, sort=False).max()
        second = self._order.nth(lead, race, 2, largest=True).reindex(top.index)
        no_history = (as_numbers(features["近5走の序盤の記録の数"]) == 0).astype("float64")
        return pd.DataFrame({
            "先頭率の合計": lead.groupby(race, sort=False).sum(),
            "先頭率の1位": top,
            "先頭率の2位": second,
            "先頭率の1位と2位の差": top - second,
            "先団率が 0.5 以上の馬の数": (front >= FRONT_RATE_LINE).astype("float64").groupby(race, sort=False).sum(),
            "先団率の合計": front.groupby(race, sort=False).sum(),
            "前にいる3頭の序盤の位置の平均": self._order.mean_of_top(
                as_numbers(features["近5走の序盤の位置の平均"]), race, _FRONT_RUNNERS, largest=False),
            "序盤の記録が無い馬の割合": no_history.groupby(race, sort=False).mean(),
            "逃げそうな馬の数": as_numbers(records.entries["lead_candidates"]).groupby(race, sort=False).first(),
            "先頭率の1位の馬の相対馬番": self._leader_position(features, race, lead),
        }, index=by_race.size().index)

    def _leader_position(self, features: pd.DataFrame, race: pd.Series, lead: pd.Series) -> pd.Series:
        """先頭率がいちばん高い馬の相対馬番。同じ値の馬がいれば、先に出てくる馬。"""
        rows = lead.groupby(race, sort=False).idxmax().dropna()
        return pd.Series(as_numbers(features.loc[rows.to_numpy(), "相対馬番"]).to_numpy(), index=rows.index)
