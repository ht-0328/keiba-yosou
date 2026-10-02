"""過去走から、末脚の履歴（N）を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers
from yosou.shared.feature.history import AsOfLookup, DatedRecords

from .early_position import EarlyPosition
from .lag_statistics import LagStatistics
from .relative_rank import RelativeRank
from .run_lags import RunLags

#: 近走として数える走の数と、重み付きの平均・同じ芝ダの平均に使う走の数（設計書 09 の N）。
RECENT_RUNS, LONG_RUNS = 5, 10
#: 横に並べる列。
_LAGGED = ("closing", "closing_top", "late_gain", "middle_gain", "against_race", "day", "surface")


class ClosingRunSummary:
    """出走の行ごとに、開催日より前の走から、末脚の履歴（N の 10個）を出す（設計書 09 の N）。

    近5走・近10走は、上がり3ハロンのある走だけを数える。上がりの速さ・4コーナーの位置・着順の位置は、
    今回の目的変数と同じ ``RelativeRank`` の物差し。「前走の上がりの速さ」は、いちばん新しい走の値。
    """

    def __init__(self) -> None:
        self._early_position = EarlyPosition()
        self._relative_rank = RelativeRank()
        self._lags = RunLags(LONG_RUNS)
        self._stats = LagStatistics()

    def build(self, entries: pd.DataFrame, past_runs: pd.DataFrame) -> pd.DataFrame:
        """行の並びと index は ``entries`` と同じ。"""
        runs = self._measured(past_runs)
        lags = self._lags.of(entries, runs[runs["closing"].notna()], _LAGGED)
        closing = lags["closing"].astype("float64")
        days_ago = self._day_numbers(entries["race_date"])[:, None] - lags["day"].astype("float64")
        same_surface = lags["surface"] == entries["surface"].to_numpy()[:, None]
        stats = self._stats
        return pd.DataFrame({
            "前走の上がりの速さ": self._previous_closing(entries, runs),
            "近5走の上がりの速さの平均": stats.mean(closing, RECENT_RUNS),
            "近5走の上がりの速さの最小": stats.minimum(closing, RECENT_RUNS),
            "近5走の上がりの速さのばらつき": stats.spread(closing, RECENT_RUNS),
            "近5走で上がりが1位だった数": stats.total(lags["closing_top"], RECENT_RUNS),
            "日数で重みを付けた上がりの速さの平均": stats.weighted_mean(closing, days_ago),
            "同じ芝ダでの上がりの速さの平均": stats.masked_mean(closing, same_surface),
            "近5走の 4コーナーからゴールまでの位置の変化の平均": stats.mean(lags["late_gain"], RECENT_RUNS),
            "近5走の序盤から 4コーナーまでの位置の変化の平均": stats.mean(lags["middle_gain"], RECENT_RUNS),
            "近5走の上がりとレースの後半タイムとの差の平均": stats.mean(lags["against_race"], RECENT_RUNS),
        }, index=entries.index)

    def _measured(self, past_runs: pd.DataFrame) -> pd.DataFrame:
        """過去走に、上がりの速さ・上がり1位か・位置の変化・レースの後半タイムとの差・日の番号を足す。"""
        rank = self._relative_rank
        closing = rank.of(past_runs["last3f_rank"], past_runs["last3f_count"])
        corner4 = rank.of(past_runs["corner4"], past_runs["field_size"])
        finish = rank.of(past_runs["finish"], past_runs["field_size"])
        early = self._early_position.of(past_runs["first_corner_rank"], past_runs["field_size"])
        return past_runs.assign(
            closing=closing,
            closing_top=(as_numbers(past_runs["last3f_rank"]) == 1).astype("float64").where(closing.notna()),
            late_gain=finish - corner4, middle_gain=corner4 - early,
            against_race=as_numbers(past_runs["last3f"]) - as_numbers(past_runs["last3f_race"]),
            day=self._day_numbers(past_runs["race_date"]),
        )

    def _previous_closing(self, entries: pd.DataFrame, runs: pd.DataFrame) -> pd.Series:
        """前走（どの走でも）の上がりの速さ。"""
        dated = DatedRecords(
            runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable"), "horse_id", "race_date",
        )
        return AsOfLookup(entries, "horse_id").latest(dated, days_before=1)["closing"]

    def _day_numbers(self, days: pd.Series) -> np.ndarray:
        """日付を、1970年1月1日からの日数にする（経過日数の引き算に使う）。"""
        return pd.to_datetime(days).to_numpy().astype("datetime64[D]").astype("float64")
