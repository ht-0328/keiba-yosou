"""S. 前半の予想の結果（1頭ごと 9個・1レースごと 6個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_ID

from .group_forecast import (
    BACK_PROBABILITY,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    MIDDLE_PROBABILITY,
    SLOW_PROBABILITY,
    GroupForecast,
)


class EarlyForecastFeatures:
    """S. 前半の予想（①②③）の結果から、後半と着順の予想の特徴量を作る（設計書 09 の S）。

    渡す予測は、そのサンプルを学習に使っていない前半のモデルの予測である（設計書 11 の決まり 11）。
    予測の無い行は欠損値になり、``StackedColumns`` が学習データから外す。
    """

    def horse(self, ids: pd.DataFrame, early: GroupForecast) -> pd.DataFrame:
        """1頭ごとの 9個。``ids`` は学習データ（予測用データ）の ID 列。index は ``ids`` と同じ。"""
        horses, races = early.horse_rows(ids), early.race_rows(ids)
        race = ids[RACE_ID]
        return pd.DataFrame({
            "先頭の確率": horses[LEADER_PROBABILITY],
            "先団の確率": horses[FRONT_PROBABILITY],
            "中団の確率": horses[MIDDLE_PROBABILITY],
            "後方の確率": horses[BACK_PROBABILITY],
            "先頭の確率のレース内順位": horses[LEADER_PROBABILITY].groupby(race).rank(method="min", ascending=False),
            "先団の確率のレース内順位": horses[FRONT_PROBABILITY].groupby(race).rank(method="min", ascending=False),
            "ハイペースの確率": races[HIGH_PROBABILITY],
            "スローペースの確率": races[SLOW_PROBABILITY],
            "前半タイムの基準との差の予測": races[FIRST_HALF_QUANTILES[1]],
        }, index=ids.index)

    def race(self, ids: pd.DataFrame, early: GroupForecast) -> pd.DataFrame:
        """1レースごとの 6個。``ids`` は1レースごとの学習データの ID 列。index は ``ids`` と同じ。"""
        races = early.race_rows(ids)
        low, middle, high = FIRST_HALF_QUANTILES
        by_race = early.horses.groupby(early.horses[RACE_ID].astype("str"))
        leader_top = by_race[LEADER_PROBABILITY].max()
        front_total = by_race[FRONT_PROBABILITY].sum()
        race_keys = ids[RACE_ID].astype("str").to_numpy()
        return pd.DataFrame({
            "ハイペースの確率": races[HIGH_PROBABILITY],
            "スローペースの確率": races[SLOW_PROBABILITY],
            "前半タイムの基準との差の予測": races[middle],
            "前半タイムの予測の幅": races[high] - races[low],
            "先頭の確率の1位": leader_top.reindex(race_keys).to_numpy(),
            "先団の確率の合計": front_total.reindex(race_keys).to_numpy(),
        }, index=ids.index)
