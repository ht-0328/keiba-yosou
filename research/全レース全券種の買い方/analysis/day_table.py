"""買う組を、セル × 開催日ごとの点数・払戻・レース数・当たったレース数に集計する。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

#: 集計する4つの値の並び（最後の軸）。点数・払戻（100円あたりの合計）・買ったレース・当たったレース。
POINTS, PAYOUT, RACES, HIT_RACES = range(4)
VALUE_COUNT = 4


class DayTable:
    """セル（◎ランク × 配当率の等級）と開催日を軸にした配列 [セル, 開催日, 4] を作り、年ごと・券種ごとに足し込む（docs/01 の 5・6）。

    ``cells`` はセルの名前の並び、``days`` は開催日の並び（どちらも位置が配列の添字）。
    ``add(combos, chosen)`` は、組の表（列 ``cell``・``race_date``・``race_id``・``payout``）のうち ``chosen`` が真の行を足し込む。
    買ったレースは、買う組が1つでもあるレース。当たったレースは、買う組の払戻が 0 より大きいレース。
    """

    def __init__(self, cells: Sequence[str], days: Sequence[pd.Timestamp]) -> None:
        self._cells = {cell: index for index, cell in enumerate(cells)}
        self._days = {pd.Timestamp(day): index for index, day in enumerate(days)}
        self.values = np.zeros((len(cells), len(days), VALUE_COUNT))

    def add(self, combos: pd.DataFrame, chosen: np.ndarray) -> None:
        rows = combos.loc[chosen, ["cell", "race_date", "race_id", "payout"]]
        if rows.empty:
            return
        per_race = rows.groupby(["cell", "race_date", "race_id"], sort=False)["payout"].agg(["size", "sum"])
        per_race["hit"] = (per_race["sum"] > 0).astype(float)
        per_day = per_race.groupby(level=["cell", "race_date"]).agg(points=("size", "sum"), payout=("sum", "sum"), races=("size", "size"), hits=("hit", "sum"))
        cell_index = per_day.index.get_level_values("cell").map(self._cells).to_numpy()
        day_index = per_day.index.get_level_values("race_date").map(lambda day: self._days[pd.Timestamp(day)]).to_numpy()
        np.add.at(self.values, (cell_index, day_index), per_day[["points", "payout", "races", "hits"]].to_numpy(dtype=float))

    def recovery(self, cell_rows: np.ndarray | None = None, day_columns: np.ndarray | None = None) -> float:
        """回収率（払戻 ÷ 投資。1点 100円）。セル・開催日を絞れる。買っていなければ NaN。"""
        picked = self._pick(cell_rows, day_columns)
        stake = picked[..., POINTS].sum() * 100.0
        return float(picked[..., PAYOUT].sum() / stake) if stake > 0 else float("nan")

    def hit_rate(self, cell_rows: np.ndarray | None = None, day_columns: np.ndarray | None = None) -> float:
        """的中率（当たったレース ÷ 買ったレース）。"""
        picked = self._pick(cell_rows, day_columns)
        races = picked[..., RACES].sum()
        return float(picked[..., HIT_RACES].sum() / races) if races > 0 else float("nan")

    def _pick(self, cell_rows: np.ndarray | None, day_columns: np.ndarray | None) -> np.ndarray:
        picked = self.values
        if cell_rows is not None:
            picked = picked[cell_rows]
        if day_columns is not None:
            picked = picked[:, day_columns]
        return picked
