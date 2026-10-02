"""レースの前半の速さ（ペース）を、同じ条件のそれより前のレースと比べて数える。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 同じ条件とみなす列（競馬場・芝ダ・距離・馬場状態）。
_CONDITION = ["venue_code", "surface", "distance_m", "condition"]
#: 基準を作るのに要る、それより前の同じ条件のレースの数。
_MIN_RACES = 20


class RacePace:
    """レースの前半の速さ: 前3F を、同じ競馬場・芝ダ・距離・馬場状態の、それより前のレースの平均と標準偏差で z にする。

    正ならハイ、負ならスロー。基準は、そのレースより前のレースだけで作る（後のレースを使わない）。
    前の同じ条件のレースが 20 より少なければ欠損値。例: 平均 35.0秒・標準偏差 0.8秒の条件で 34.2秒なら +1.0（ハイ）。
    同じ日のレースは、レースID の順（同じ競馬場ならレース番号の順）に前とみなす。並びを決めておかないと、学習と予測で
    並びが変わって値がずれる（研究では開催日だけで並べていた）。
    """

    def of(self, runs: pd.DataFrame) -> pd.Series:
        """レースID → ペース。``runs`` は出走の行（race_id・race_date・条件の列・first3f）。"""
        races = runs.drop_duplicates("race_id")[["race_id", "race_date", *_CONDITION, "first3f"]]
        races = races.sort_values(["race_date", "race_id"], kind="stable")
        first3f = pd.to_numeric(races["first3f"], errors="coerce").astype(float)
        keys = [races[column] for column in _CONDITION]
        count = first3f.groupby(keys, sort=False).cumcount()
        mean = (first3f.groupby(keys, sort=False).cumsum() - first3f) / count.where(count > 0)
        square = (first3f ** 2).groupby(keys, sort=False).cumsum() - first3f ** 2
        std = np.sqrt((square / count.where(count > 0) - mean ** 2).clip(lower=1e-6))
        pace = -(first3f - mean) / std
        return pd.Series(pace.where(count >= _MIN_RACES).to_numpy(), index=races["race_id"].to_numpy())
