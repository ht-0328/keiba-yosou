"""走ごとのスピード指数から、「そのレースの時点での馬の力」の特徴量を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 見る過去走の数と期間（研究「能力指数の作り方」で決めた値）。
_RUNS, _WINDOW_DAYS = 8, 730
#: 1つ古い走の重みの倍率と、条件の近さの重み（同じ研究の値）。
_RECENCY, _DISTANCE_SCALE, _OTHER_VENUE, _OTHER_GOING, _OTHER_SURFACE = 0.7, 800.0, 0.9, 0.8, 0.4
#: 馬場の組（良・稍重 と 重・不良）。
_HEAVY = {"重", "不良", "不"}

FIGURE = "スピード指数"


class AbilityFeatures:
    """``figures``（1行 = 1回の走。研究「能力指数の作り方」の中間データ）から、各走の「その走より前の走だけ」で作った特徴量。

    どれもその走の結果は使わないので、これから走るレースにも同じ形で付けられる。
    列: rid・horse_no と、次の特徴量。
    - 指数_前走・指数_近5走の最高・指数_近3走の平均: そのまま
    - 指数_新しさの重み: 近8走（2年以内）を 1つ古いごとに 0.7倍して平均
    - 指数_条件の重み: 新しさの重みに、今回との距離・競馬場・芝ダ・馬場の組の近さの重みを掛けて平均（能力指数と同じ）
    - 着順_前走・着順_近3走の平均、出走数、前走からの日数、距離の変化、前走と芝ダが同じか
    """

    def build(self, figures: pd.DataFrame) -> pd.DataFrame:
        runs = self._prepare(figures)
        grouped = runs.groupby("horse_id", sort=False)
        lags = {k: self._lag(grouped, k) for k in range(1, _RUNS + 1)}
        result = pd.DataFrame({"rid": runs["race_id"], "horse_no": runs["horse_no"]})
        figures_by_lag = np.column_stack([lags[k]["fig"] for k in lags])
        usable = np.column_stack([self._usable(runs, lags[k]) for k in lags])
        recency = _RECENCY ** np.arange(_RUNS)
        nearness = np.column_stack([self._nearness(runs, lags[k]) for k in lags])
        result["指数_前走"] = np.where(usable[:, 0], figures_by_lag[:, 0], np.nan)
        result["指数_近5走の最高"] = self._masked(figures_by_lag[:, :5], usable[:, :5]).max(axis=1)
        result["指数_近3走の平均"] = self._masked(figures_by_lag[:, :3], usable[:, :3]).mean(axis=1)
        result["指数_新しさの重み"] = self._weighted(figures_by_lag, usable, recency[None, :])
        result["指数_条件の重み"] = self._weighted(figures_by_lag, usable, recency[None, :] * nearness)
        result["指数_伸び"] = result["指数_前走"] - result["指数_近3走の平均"]
        result["着順_前走"] = lags[1]["finish"]
        result["着順_近3走の平均"] = np.nanmean(np.column_stack([lags[k]["finish"] for k in (1, 2, 3)]), axis=1)
        result["出走数"] = grouped.cumcount()
        result["前走からの日数"] = (runs["race_date"] - lags[1]["date"]).dt.days
        result["距離の変化"] = runs["distance_m"] - lags[1]["distance"]
        result["前走と芝ダが同じ"] = (runs["surface_code"] == lags[1]["surface"]).astype(float)
        return result

    def _prepare(self, figures: pd.DataFrame) -> pd.DataFrame:
        runs = figures.sort_values(["horse_id", "race_date", "race_id"]).reset_index(drop=True)
        return runs.assign(surface_code=pd.factorize(runs["surface"])[0],
                           venue_int=pd.to_numeric(runs["venue_code"], errors="coerce"),
                           heavy=runs["condition"].isin(_HEAVY).astype(int))

    def _lag(self, grouped, k: int) -> dict[str, pd.Series]:
        return {"fig": grouped[FIGURE].shift(k), "date": grouped["race_date"].shift(k),
                "distance": grouped["distance_m"].shift(k), "surface": grouped["surface_code"].shift(k),
                "venue": grouped["venue_int"].shift(k), "heavy": grouped["heavy"].shift(k),
                "finish": grouped["finish"].shift(k)}

    def _usable(self, runs: pd.DataFrame, lag: dict[str, pd.Series]) -> np.ndarray:
        days = (runs["race_date"] - lag["date"]).dt.days
        return (lag["fig"].notna() & (days <= _WINDOW_DAYS)).to_numpy()

    def _nearness(self, runs: pd.DataFrame, lag: dict[str, pd.Series]) -> np.ndarray:
        distance = np.exp(-(runs["distance_m"] - lag["distance"]).abs() / _DISTANCE_SCALE)
        venue = np.where(runs["venue_int"] == lag["venue"], 1.0, _OTHER_VENUE)
        surface = np.where(runs["surface_code"] == lag["surface"], 1.0, _OTHER_SURFACE)
        going = np.where(runs["heavy"] == lag["heavy"], 1.0, _OTHER_GOING)
        return np.nan_to_num((distance * venue * surface * going).to_numpy(dtype=float))

    def _masked(self, values: np.ndarray, usable: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame(np.where(usable, values, np.nan))

    def _weighted(self, values: np.ndarray, usable: np.ndarray, weights: np.ndarray) -> np.ndarray:
        used = np.where(usable, weights, 0.0)
        total = used.sum(axis=1)
        summed = (np.nan_to_num(values) * used).sum(axis=1)
        return np.where(total > 0, summed / np.where(total > 0, total, 1.0), np.nan)
