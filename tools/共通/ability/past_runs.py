"""各出走に、その馬の前の走を横に並べる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .speed_figure import FIGURE

#: 並べる列。
_COLUMNS: tuple[str, ...] = (FIGURE, "race_date", "distance_m", "surface", "venue_code", "condition")
#: 良・稍重を「良」、重・不良を「道悪」とする。
_GOING = {"良": "良", "稍重": "良", "重": "道悪", "不良": "道悪"}


class PastRuns:
    """出走の表（開催日の順）の各行について、同じ馬の1つ前〜``depth`` 個前の走を、(行数, depth) の配列にして持つ。

    ``window_days`` より前の走と、スピード指数の無い走は、指数を欠損値にする（使わない）。
    例: ``depth`` 3 で、前走・2走前・3走前の指数が 85・80・（2年より前）なら、指数の行は [85, 80, NaN]。
    """

    def __init__(self, runs: pd.DataFrame, depth: int, window_days: int) -> None:
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        grouped = ordered.groupby("horse_id", sort=False)
        lags = {column: np.column_stack([grouped[column].shift(k).to_numpy() for k in range(1, depth + 1)])
                for column in _COLUMNS}
        position = pd.Series(np.arange(len(ordered)), index=ordered.index).reindex(runs.index).to_numpy()
        self._lags = {column: values[position] for column, values in lags.items()}
        days = (runs["race_date"].to_numpy()[:, None] - self._lags["race_date"].astype("datetime64[ns]"))
        recent = days <= np.timedelta64(window_days, "D")
        self.figure = np.where(recent, self._lags[FIGURE].astype(float), np.nan)

    def same(self, column: str, values: pd.Series) -> np.ndarray:
        """前の走の ``column`` が、今回の値（``values``）と同じか。"""
        return self._lags[column] == values.to_numpy()[:, None]

    def distance_gap(self, distance: pd.Series) -> np.ndarray:
        """前の走の距離と、今回の距離の差（m、絶対値）。"""
        return np.abs(self._lags["distance_m"].astype(float) - distance.to_numpy(dtype=float)[:, None])

    def same_going(self, condition: pd.Series) -> np.ndarray:
        """前の走の馬場が、今回と同じ組（良・稍重 か、重・不良）か。"""
        lags = self._lags["condition"]
        past = pd.Series(lags.ravel()).map(_GOING).fillna("").to_numpy().reshape(lags.shape)
        now = condition.map(_GOING).fillna("?").to_numpy()[:, None]
        return past == now
