"""条件の標準タイムと比べた速さ（能力指数）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature.history import AsOfLookup, DatedRecords

#: 特徴量の名前。
LAST = "前走の速度指数"
BEST = "近5走の最高速度指数"
MEAN = "近5走の平均速度指数"
BEST_RANK = "近5走の最高速度指数のレース内順位"
NAMES: tuple[str, ...] = (LAST, BEST, MEAN, BEST_RANK)
#: 条件の鍵（競馬場・芝ダ・距離・馬場状態）と、標準タイムを出すのに要る前の年までの走の数。
_KEY = ["venue_code", "surface", "distance_m", "condition_code"]
_MIN_RUNS = 30
_RECENT = 5


class SpeedFigureFeatures:
    """能力指数（既存モデルの修正計画の 4「条件を補正したタイムの能力指数」）。

    同じ競馬場・芝ダ・距離・馬場状態の「標準タイム」（前の年までの走破タイムの中央値を、年ごとの走の数で重み付けした平均）
    と比べて、何%速かったか: 速度指数 = (標準タイム − 走破タイム) ÷ 標準タイム × 100。
    例: 標準 96.0秒の条件を 95.5秒で走れば +0.52。前の年までに 30走に満たない条件は欠損値。
    馬ごとに、開催日の前日までの前走・近5走の最高・近5走の平均と、近5走の最高のレース内順位を特徴量にする。
    """

    def build(self, history: pd.DataFrame) -> pd.DataFrame:
        """列は race_id・horse_id と ``NAMES``。"""
        runs = self._with_figure(history)
        summary = self._recent(runs)
        dated = DatedRecords(summary, key_column="horse_id", date_column="race_date")
        found = AsOfLookup(history[["race_id", "horse_id", "race_date"]], "horse_id").latest(dated, days_before=1)
        features = history[["race_id", "horse_id"]].assign(**{name: found[name].to_numpy() for name in (LAST, BEST, MEAN)})
        rank = features[BEST].groupby(features["race_id"]).rank(ascending=False, method="min")
        return features.assign(**{BEST_RANK: rank})

    def _with_figure(self, history: pd.DataFrame) -> pd.DataFrame:
        """走ごとの速度指数。標準タイムは、その走の年より前の年だけから作る。"""
        runs = history.assign(year=history["race_date"].dt.year,
                              time=pd.to_numeric(history["finish_time"], errors="coerce"))
        runs = runs[runs["time"] > 0]
        yearly = runs.groupby([*_KEY, "year"], as_index=False).agg(median=("time", "median"), runs=("time", "size"))
        standard = self._prior_standard(yearly)
        merged = runs.merge(standard, on=[*_KEY, "year"], how="left")
        figure = (merged["standard"] - merged["time"]) / merged["standard"] * 100.0
        return merged.assign(figure=figure)[["horse_id", "race_date", "race_id", "figure"]]

    def _prior_standard(self, yearly: pd.DataFrame) -> pd.DataFrame:
        """条件 × 年 → 前の年までの標準タイム（走の数が足りなければ欠損値）。"""
        ordered = yearly.sort_values([*_KEY, "year"])
        grouped = ordered.groupby(_KEY, sort=False)
        weighted = (ordered["median"] * ordered["runs"]).groupby([ordered[key] for key in _KEY]).cumsum()
        counted = grouped["runs"].cumsum()
        prior_weighted = weighted - ordered["median"] * ordered["runs"]
        prior_runs = counted - ordered["runs"]
        standard = (prior_weighted / prior_runs).where(prior_runs >= _MIN_RUNS)
        return ordered[[*_KEY, "year"]].assign(standard=standard)

    def _recent(self, runs: pd.DataFrame) -> pd.DataFrame:
        """走ごとの、その走までの前走・近5走の最高・近5走の平均（馬・開催日の古い順）。"""
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable").reset_index(drop=True)
        rolling = ordered.groupby("horse_id", sort=False)["figure"].rolling(_RECENT, min_periods=1)
        return pd.DataFrame({
            "horse_id": ordered["horse_id"], "race_date": ordered["race_date"],
            LAST: ordered["figure"].to_numpy(),
            BEST: rolling.max().reset_index(level=0, drop=True).to_numpy(),
            MEAN: rolling.mean().reset_index(level=0, drop=True).to_numpy(),
        }).replace([np.inf, -np.inf], np.nan)
