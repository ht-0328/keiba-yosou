"""過去走から、序盤の位置取りの履歴（K）を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers
from yosou.shared.feature.history import AsOfLookup, DatedRecords

from .early_position import EarlyPosition
from .lag_statistics import LagStatistics
from .relative_rank import RelativeRank
from .run_lags import RunLags
from .smoothed_rate import SmoothedRate

#: 近走として数える走の数と、先頭率・重み付きの平均などに使う走の数（設計書 09 の K）。
RECENT_RUNS, LONG_RUNS = 5, 10
#: 横に並べる列。
_LAGGED = ("position", "lead", "front", "day", "surface")


class EarlyRunSummary:
    """出走の行ごとに、開催日より前の走から、序盤の位置取りの履歴（K のうち騎手の2個を除く 13個）を出す（設計書 09 の K）。

    近5走・近10走は、序盤の位置のある走（直線コースとコーナーを5回以上通るレースを除く）だけを数える。
    「前走の…」は、序盤の位置の有無によらず、いちばん新しい走の値。
    """

    def __init__(self) -> None:
        self._early_position = EarlyPosition()
        self._relative_rank = RelativeRank()
        self._lags = RunLags(LONG_RUNS)
        self._stats = LagStatistics()
        self._smoothed = SmoothedRate()

    def build(self, entries: pd.DataFrame, past_runs: pd.DataFrame, prior: pd.DataFrame) -> pd.DataFrame:
        """``prior`` は出走の行ごとの全体の先頭率・先団率（列 ``lead``・``front``）。行の並びと index は ``entries`` と同じ。"""
        runs = self._measured(past_runs)
        lags = self._lags.of(entries, runs[runs["position"].notna()], _LAGGED)
        position, lead, front = lags["position"], lags["lead"], lags["front"]
        days_ago = self._day_numbers(entries["race_date"])[:, None] - lags["day"].astype("float64")
        same_surface = lags["surface"] == entries["surface"].to_numpy()[:, None]
        long_count = self._stats.count(position, LONG_RUNS)
        stats = self._stats
        summary = pd.DataFrame({
            "近5走の序盤の位置の平均": stats.mean(position, RECENT_RUNS),
            "近5走の序盤の位置の最小": stats.minimum(position, RECENT_RUNS),
            "近5走の序盤の位置のばらつき": stats.spread(position, RECENT_RUNS),
            "近5走の序盤の記録の数": stats.count(position, RECENT_RUNS),
            "近5走の先頭の数": stats.total(lead, RECENT_RUNS),
            "近5走の先団の数": stats.total(front, RECENT_RUNS),
            "先頭率": self._smoothed.of(stats.total(lead, LONG_RUNS), long_count, prior["lead"].to_numpy()),
            "先団率": self._smoothed.of(stats.total(front, LONG_RUNS), long_count, prior["front"].to_numpy()),
            "日数で重みを付けた序盤の位置の平均": stats.weighted_mean(position.astype("float64"), days_ago),
            "同じ芝ダでの序盤の位置の平均": stats.masked_mean(position, same_surface),
        }, index=entries.index)
        return pd.concat([self._previous_run(entries, runs), summary], axis=1)

    def _measured(self, past_runs: pd.DataFrame) -> pd.DataFrame:
        """過去走に、序盤の位置・先頭か・先団か・4コーナーの位置・日の番号を足す。"""
        position = self._early_position.of(past_runs["first_corner_rank"], past_runs["field_size"])
        is_lead = (as_numbers(past_runs["first_corner_rank"]) == 1).astype("float64").where(position.notna())
        return past_runs.assign(
            position=position, lead=is_lead, front=self._early_position.is_front(position),
            corner4_position=self._relative_rank.of(past_runs["corner4"], past_runs["field_size"]),
            day=self._day_numbers(past_runs["race_date"]),
        )

    def _previous_run(self, entries: pd.DataFrame, runs: pd.DataFrame) -> pd.DataFrame:
        """前走（どの走でも）の序盤の位置、序盤から4コーナーへの位置の変化、今回との距離の差。"""
        dated = DatedRecords(
            runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable"), "horse_id", "race_date",
        )
        previous = AsOfLookup(entries, "horse_id").latest(dated, days_before=1)
        return pd.DataFrame({
            "前走の序盤の位置": previous["position"],
            "前走の序盤から4コーナーへの位置の変化": previous["corner4_position"] - previous["position"],
            "前走からの距離の差": as_numbers(entries["distance_m"]) - as_numbers(previous["distance_m"]),
        }, index=entries.index)

    def _day_numbers(self, days: pd.Series) -> np.ndarray:
        """日付を、1970年1月1日からの日数にする（経過日数の引き算に使う）。"""
        return pd.to_datetime(days).to_numpy().astype("datetime64[D]").astype("float64")
