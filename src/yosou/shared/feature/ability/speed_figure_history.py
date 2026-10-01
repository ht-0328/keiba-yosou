"""走ごとのスピード指数から、「そのレースの時点での馬の力」の列を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 見る過去走の数と期間（研究「能力指数の作り方」で決めた値）。
_RUNS, _WINDOW_DAYS = 8, 730
#: 1つ古い走の重みの倍率と、条件の近さの重み（同じ研究の値）。
_RECENCY, _DISTANCE_SCALE, _OTHER_VENUE, _OTHER_GOING, _OTHER_SURFACE = 0.7, 800.0, 0.9, 0.8, 0.4
#: 馬場の組（良・稍重 と 重・不良）。
_HEAVY = {"重", "不良", "不"}


class SpeedFigureHistory:
    """走ごとの表（``figure`` はスピード指数）から、各走の「その走より前の走だけ」で作った列を返す。

    どれもその走の結果は使わないので、これから走るレースにも同じ形で付けられる（その行の ``figure`` は欠損値でよい）。
    列は race_id・horse_id と ``FIGURE_COLUMNS``（ability_columns.py）。
    - 指数_前走・指数_近5走の最高・指数_近3走の平均: そのまま（2年より前の走は使わない）
    - 指数_新しさの重み: 近8走（2年以内）を 1つ古いごとに 0.7倍して平均
    - 指数_条件の重み: 新しさの重みに、今回との距離・競馬場・芝ダ・馬場の組の近さの重みを掛けて平均
    - 指数_伸び: 前走 − 近3走の平均
    - 着順_前走・着順_近3走の平均、出走数、前走からの日数、距離の変化、前走と芝ダが同じか
    例: 前走 80・2走前 76 で、2走前が今回と 400m 違うなら、条件の重みは 80 × 1 と 76 × 0.7 × 0.61 の重み付き平均。
    """

    def build(self, figures: pd.DataFrame) -> pd.DataFrame:
        runs = self._prepare(figures)
        grouped = runs.groupby("horse_id", sort=False)
        lags = {k: self._lag(grouped, k) for k in range(1, _RUNS + 1)}
        result = pd.DataFrame({"race_id": runs["race_id"], "horse_id": runs["horse_id"]})
        by_lag = np.column_stack([lags[k]["fig"] for k in lags])
        usable = np.column_stack([self._usable(runs, lags[k]) for k in lags])
        recency = _RECENCY ** np.arange(_RUNS)
        nearness = np.column_stack([self._nearness(runs, lags[k]) for k in lags])
        result["指数_前走"] = np.where(usable[:, 0], by_lag[:, 0], np.nan)
        result["指数_近5走の最高"] = self._masked(by_lag[:, :5], usable[:, :5]).max(axis=1).to_numpy()
        result["指数_近3走の平均"] = self._masked(by_lag[:, :3], usable[:, :3]).mean(axis=1).to_numpy()
        result["指数_新しさの重み"] = self._weighted(by_lag, usable, recency[None, :])
        result["指数_条件の重み"] = self._weighted(by_lag, usable, recency[None, :] * nearness)
        result["指数_伸び"] = result["指数_前走"] - result["指数_近3走の平均"]
        result["着順_前走"] = lags[1]["finish"]
        result["着順_近3走の平均"] = self._nan_mean(np.column_stack([lags[k]["finish"] for k in (1, 2, 3)]))
        result["出走数"] = grouped.cumcount()
        result["前走からの日数"] = (runs["race_date"] - lags[1]["date"]).dt.days
        result["距離の変化"] = runs["distance_m"] - lags[1]["distance"]
        result["前走と芝ダが同じ"] = (runs["surface_code"] == lags[1]["surface"]).astype(float)
        return result

    def _prepare(self, figures: pd.DataFrame) -> pd.DataFrame:
        runs = figures.sort_values(["horse_id", "race_date", "race_id"]).reset_index(drop=True)
        numeric = runs[["distance_m", "finish"]].apply(lambda column: pd.to_numeric(column, errors="coerce"))
        return runs.assign(distance_m=numeric["distance_m"].astype(float), finish=numeric["finish"].astype(float),
                           race_date=pd.to_datetime(runs["race_date"]),
                           surface_code=pd.factorize(runs["surface"])[0],
                           venue_int=pd.to_numeric(runs["venue_code"], errors="coerce"),
                           heavy=runs["condition"].isin(_HEAVY).astype(int))

    def _lag(self, grouped, k: int) -> dict[str, pd.Series]:
        return {"fig": grouped["figure"].shift(k), "date": grouped["race_date"].shift(k),
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

    def _nan_mean(self, values: np.ndarray) -> np.ndarray:
        """行ごとの欠損値を除いた平均。全部欠損値の行は欠損値（警告を出さない）。"""
        counts = np.isfinite(values).sum(axis=1)
        sums = np.nansum(values, axis=1)
        return np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
