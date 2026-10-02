"""1つの券種の、レースごとの組み合わせと確定オッズ。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RaceCombinations:
    """1レース・1つの券種の組み合わせ。``horses`` は（組の数 × 馬の数）の馬番、``odds`` は確定オッズ（倍）。

    複勝・ワイドは払戻が幅で決まるので、``odds`` は最低、``odds_high`` は最高。ほかの券種の ``odds_high`` は ``odds`` と同じ。
    """

    horses: np.ndarray
    odds: np.ndarray
    odds_high: np.ndarray

    def __len__(self) -> int:
        return len(self.odds)


#: 組み合わせの無いレースの値（券種ごとの馬の数に合わせて作る）。
def _empty(width: int) -> RaceCombinations:
    return RaceCombinations(np.zeros((0, width), dtype=int), np.zeros(0), np.zeros(0))


class CombinationTable:
    """1つの券種の、期間の全レースの組み合わせと確定オッズ。``race`` でレースごとに引く。

    ``frame`` の列は ``race_id``・``h1``（〜``h3``。馬の数だけ）・``odds``・``odds_high``。
    """

    def __init__(self, frame: pd.DataFrame, width: int) -> None:
        self._width = width
        ordered = frame.sort_values("race_id", kind="stable").reset_index(drop=True)
        horse_columns = [f"h{position}" for position in range(1, width + 1)]
        self._horses = ordered[horse_columns].to_numpy(dtype=int)
        self._odds = ordered["odds"].to_numpy(dtype="float64")
        self._odds_high = ordered["odds_high"].to_numpy(dtype="float64")
        race_ids = ordered["race_id"].astype(str).to_numpy()
        starts = np.flatnonzero(np.r_[True, race_ids[1:] != race_ids[:-1]]) if len(race_ids) else np.zeros(0, dtype=int)
        ends = np.r_[starts[1:], len(race_ids)] if len(race_ids) else np.zeros(0, dtype=int)
        self._slices = {race_ids[start]: (start, end) for start, end in zip(starts, ends)}

    @property
    def race_ids(self) -> set[str]:
        return set(self._slices)

    def race(self, race_id: str) -> RaceCombinations:
        """そのレースの組み合わせ。無ければ空。"""
        found = self._slices.get(str(race_id))
        if found is None:
            return _empty(self._width)
        start, end = found
        return RaceCombinations(self._horses[start:end], self._odds[start:end], self._odds_high[start:end])
