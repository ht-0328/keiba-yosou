"""中穴・大穴（4番人気以下）が2頭以上3着以内に来る確率と、中穴・大穴2頭の組の確率を、展開の型ごとに出して混ぜる。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd

#: 1頭の3着以内の確率の上限（そろえたあとで 1 を超えないように）。
_CAP = 0.95


@dataclass(frozen=True)
class PairProbability:
    """``frame`` は ``EvaluationFrame`` の表に、レースごとの混ぜる重み w_0〜w_2（スロー・平均・ハイ）を足したもの。
    ``columns`` は展開の型ごとの3着以内の確率の列（3つ）。展開の型ごとに、レースの全頭の確率の合計が 3 になるようにそろえ、
    その中では各馬が独立に来るとみなして、組の確率と2頭以上の確率を出し、重みで混ぜる。市場と比べるときは、3つとも同じ列を渡す。

    ``races`` は1行 = 1レース（race_id・period・two_or_more（2頭以上の確率）・pair（いちばん確率の高い組の馬番 'a-b'）・
    pair_probability・actual（実際に3着以内に来た4番人気以下の頭数）・actual_pair（実際の組。2頭以上のとき、確率の高い順の組の1つ目））、
    ``pairs`` は1行 = 1組（race_id・pair・probability・hit（2頭とも3着以内））。"""

    columns: tuple[str, str, str]
    first_outsider: int = 4

    def races(self, frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        race_rows, pair_rows = [], []
        for race_id, race in frame.groupby("race_id", sort=False):
            normalized = self._normalized(race)
            outsiders = (race["popularity"] >= self.first_outsider).to_numpy()
            weights = race[["w_0", "w_1", "w_2"]].iloc[0].to_numpy(dtype=float)
            numbers = race["horse_no"].to_numpy()
            placed = (race["y_top3"] > 0).to_numpy()
            q = normalized[outsiders]
            two = float(sum(weight * self._two_or_more(q[:, index]) for index, weight in enumerate(weights)))
            pairs = [(numbers[outsiders][a], numbers[outsiders][b], float((weights * q[a] * q[b]).sum()),
                      bool(placed[outsiders][a] and placed[outsiders][b])) for a, b in combinations(range(len(q)), 2)]
            pairs.sort(key=lambda item: -item[2])
            best = pairs[0] if pairs else (None, None, np.nan, False)
            race_rows.append({"race_id": race_id, "period": race["period"].iloc[0], "two_or_more": two,
                              "pair": f"{int(best[0])}-{int(best[1])}" if best[0] is not None else "", "pair_probability": best[2],
                              "pair_hit": best[3], "actual": int(placed[outsiders].sum())})
            pair_rows.extend({"race_id": race_id, "pair": f"{int(a)}-{int(b)}", "probability": p, "hit": hit, "rank": rank}
                             for rank, (a, b, p, hit) in enumerate(pairs[:10], start=1))
        return pd.DataFrame(race_rows), pd.DataFrame(pair_rows)

    def _normalized(self, race: pd.DataFrame) -> np.ndarray:
        values = race[list(self.columns)].to_numpy(dtype=float)
        return np.clip(values * 3.0 / values.sum(axis=0, keepdims=True), 0.0, _CAP)

    @staticmethod
    def _two_or_more(q: np.ndarray) -> float:
        """独立に来るとみなしたとき、2頭以上が来る確率（1 − 0頭の確率 − ちょうど1頭の確率）。"""
        if len(q) < 2:
            return 0.0
        none = float(np.prod(1 - q))
        one = float(sum(q[i] * np.prod(np.delete(1 - q, i)) for i in range(len(q))))
        return 1.0 - none - one
