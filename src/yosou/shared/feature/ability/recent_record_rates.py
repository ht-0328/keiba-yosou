"""区分（騎手・調教師）ごとの、直近の期間だけの成績を、日付の順に数える。"""

from __future__ import annotations

import pandas as pd

from .ability_columns import PLACE_PRIOR, WIN_PRIOR

#: 件数が少ないときに全体の平均へ寄せる強さ（出走数で数える）。
_SHRINK = 50.0
_CUMULATIVE = ["cum_runs", "cum_wins", "cum_places"]


class RecentRecordRates:
    """開催日の前日までの ``window_days`` 日間の勝率と3着内率を、区分ごとに数える。

    通算の成績（``CumulativeRecordRates``）と違い、騎手の腕や厩舎の調子の今を表す。
    ``rate_on`` で、任意の区分と日付の組（例: 前走の騎手と今回の日付）の成績も引ける。
    件数が少ない区分は、全体の値（``WIN_PRIOR``・``PLACE_PRIOR``）に寄せる。
    例: 騎手A の前日までの1年間が 400戦40勝なら、全体の勝率 0.07 として (40 + 3.5) ÷ 450 = 0.097。
    ``runs`` は出走した馬の行（``finish`` は数）。
    """

    def __init__(self, runs: pd.DataFrame, key: str, window_days: int) -> None:
        valid = runs[runs[key].notna()]
        scored = valid.assign(won=(valid["finish"] == 1).astype(float), placed=(valid["finish"] <= 3).astype(float))
        daily = scored.groupby([key, "race_date"], as_index=False).agg(
            runs=("won", "size"), wins=("won", "sum"), places=("placed", "sum")).sort_values([key, "race_date"])
        grouped = daily.groupby(key, sort=False)
        for column in ("runs", "wins", "places"):
            daily[f"cum_{column}"] = grouped[column].cumsum()
        self._key = key
        self._window = pd.Timedelta(days=window_days)
        # merge_asof は、右の表が日付の順（区分をまたいで）に並んでいることを求める。
        self._daily = daily.sort_values("race_date", kind="stable")

    def rate_on(self, codes: pd.Series, dates: pd.Series) -> pd.DataFrame:
        """区分の値と日付の組ごとの（win 勝率, place 3着内率）。日付の当日は数えない。行の並びは ``codes`` と同じ。"""
        query = pd.DataFrame({self._key: codes.to_numpy(), "race_date": pd.to_datetime(dates).to_numpy(),
                              "order": range(len(codes))})
        before = self._cumulative_before(query, query["race_date"])
        start = self._cumulative_before(query, query["race_date"] - self._window)
        runs = before["cum_runs"] - start["cum_runs"]
        wins = before["cum_wins"] - start["cum_wins"]
        places = before["cum_places"] - start["cum_places"]
        return pd.DataFrame({"win": (wins + _SHRINK * WIN_PRIOR) / (runs + _SHRINK),
                             "place": (places + _SHRINK * PLACE_PRIOR) / (runs + _SHRINK)})

    def _cumulative_before(self, query: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
        """その日付の前日までの累積（出走・勝ち・3着内）。区分の値が無い行や、まだ走っていない区分は 0。"""
        left = query.assign(race_date=dates - pd.Timedelta(days=1)).sort_values("race_date")
        # 区分の型を右の表にそろえる（新馬戦の前走の騎手のように全部が欠損値だと、型の違う空の列になり merge_asof が止まる）
        valid = left[left[self._key].notna()].astype({self._key: self._daily[self._key].dtype})
        found = pd.merge_asof(valid, self._daily[[self._key, "race_date", *_CUMULATIVE]],
                              on="race_date", by=self._key, direction="backward")
        found = found.set_index("order").reindex(range(len(query)))
        return found[_CUMULATIVE].fillna(0.0).reset_index(drop=True)
