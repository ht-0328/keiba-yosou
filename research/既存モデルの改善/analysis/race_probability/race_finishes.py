"""レースごとの、勝率と1〜3着の馬の位置の並びを作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class RaceFinishes:
    """1行 = 1頭の表から、レースごとに（勝率の配列, 1着の位置, 2着の位置, 3着の位置）を作る。

    ``SternExponentFitter`` が「実際の 1着 → 2着 → 3着 の並びが、いちばん起きやすくなる補正」を探すのに使う。
    1〜3着のどれかがちょうど1頭でないレース（同着・競走中止）は使わない。
    """

    def build(self, race_ids: pd.Series, probability: pd.Series,
              finish: pd.Series) -> list[tuple[np.ndarray, int, int, int]]:
        table = pd.DataFrame({"race": race_ids.to_numpy(), "p": probability.to_numpy(), "finish": finish.to_numpy()})
        return [race for race in (self._one(group) for _, group in table.groupby("race", sort=False)) if race is not None]

    def _one(self, group: pd.DataFrame) -> tuple[np.ndarray, int, int, int] | None:
        finish = group["finish"].to_numpy()
        positions = [np.flatnonzero(finish == rank) for rank in (1, 2, 3)]
        if any(len(found) != 1 for found in positions):
            return None
        probability = group["p"].to_numpy(dtype="float64")
        return probability / probability.sum(), int(positions[0][0]), int(positions[1][0]), int(positions[2][0])
