"""ワイドの組の、Harville の式での確率。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .column_names import HORSE_NO, RACE_ID
from .harville_probability import HarvilleProbability

_VALUE = "pair_in_top3"
_PAIR_COLUMNS = [RACE_ID, "h1", "h2", _VALUE]


class WidePairProbability:
    """ワイドの組（2頭とも3着以内）の確率を、レースの全頭の1着の確率から Harville の式で出す。

    3頭目は、組の2頭のほかの全部の出走馬（馬ごとの材料の表にいる馬）で足す。
    例: 1着の確率が 0.5・0.3・0.2 の3頭のレースでは、どの2頭も必ず3着以内なので、どの組も 1.0。
    """

    def __init__(self) -> None:
        self._harville = HarvilleProbability()

    def of(self, rows: pd.DataFrame, materials: pd.DataFrame, share: str) -> np.ndarray:
        """``rows`` はワイドの行（列 ``race_id``・``h1``・``h2``。馬番の小さい順）、``materials`` は馬ごとの材料の表、
        ``share`` は1着の確率の列（``pwn`` か ``mwn``）。戻り値は ``rows`` と同じ並びの確率。"""
        in_rows = materials[materials[RACE_ID].isin(set(rows[RACE_ID]))]
        races = in_rows.sort_values(HORSE_NO, kind="stable").groupby(RACE_ID, sort=False)
        parts = [self._race_pairs(race_id, race, share) for race_id, race in races]
        pairs = pd.concat([pd.DataFrame(columns=_PAIR_COLUMNS), *parts], ignore_index=True)
        wanted = rows[[RACE_ID, "h1", "h2"]].astype({"h1": np.int64, "h2": np.int64})
        found = wanted.merge(pairs.astype({"h1": np.int64, "h2": np.int64}), on=[RACE_ID, "h1", "h2"], how="left")
        return found[_VALUE].to_numpy(dtype=float)

    def _race_pairs(self, race_id: str, race: pd.DataFrame, share: str) -> pd.DataFrame:
        """1レースの全部の2頭の組（馬番の小さい順）の確率。``race`` は馬番の小さい順の行。"""
        numbers = race[HORSE_NO].to_numpy(dtype=np.int64)
        matrix = self._harville.pairs_in_top3(race[share].to_numpy(dtype=float))
        first, second = np.triu_indices(len(numbers), k=1)
        return pd.DataFrame({RACE_ID: race_id, "h1": numbers[first], "h2": numbers[second], _VALUE: matrix[first, second]})
