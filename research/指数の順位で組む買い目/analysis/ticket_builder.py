"""順位の表と形から、買い目（1行 = 1点）を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .formation import Formation
from .rank_table import FIELD

#: 組の数（馬番を2桁ずつ並べた組番を数にしたもの。``0105`` → 105、``010512`` → 10512。払戻の組番と突き合わせる鍵）。
COMBO = "combo"
#: 買い目の表の列。
COLUMNS: tuple[str, ...] = ("race_id", COMBO)


class TicketBuilder:
    """順位の表（``RankTable.build``）の ``rank_column`` の順位に形を当て、買い目を作る。

    頭数ごとに「順位の組」を1回作り、順位 → 馬番の表（レース × 順位）に当てて全レースぶんを一度に組む。
    順番を問わない券種は馬番を昇順に並べる（払戻の組番と同じ並び）。頭数が足りない順位の組は作らない。
    """

    def build(self, ranked: pd.DataFrame, rank_column: str, formation: Formation) -> pd.DataFrame:
        parts = []
        for field, group in ranked.groupby(FIELD, sort=True):
            combos = formation.rank_combos(int(field))
            if not combos:
                continue
            ordered = group.sort_values(["race_id", rank_column], kind="stable")
            race_ids = ordered["race_id"].to_numpy()[:: int(field)]
            horses = ordered["horse_no"].to_numpy(dtype=np.int64).reshape(-1, int(field))
            picked = horses[:, np.asarray(combos, dtype=np.int64) - 1]
            if not formation.ordered:
                picked = np.sort(picked, axis=2)
            flat = picked.reshape(-1, formation.horse_count)
            parts.append(pd.DataFrame({"race_id": np.repeat(race_ids, len(combos)), COMBO: self.combo_code(flat)}))
        if not parts:
            return pd.DataFrame({"race_id": pd.Series(dtype=str), COMBO: pd.Series(dtype=np.int64)})
        return pd.concat(parts, ignore_index=True)

    @staticmethod
    def combo_code(horses: np.ndarray) -> np.ndarray:
        """馬番の並び（行 × 馬の数）を組の数にする。"""
        code = np.zeros(len(horses), dtype=np.int64)
        for column in range(horses.shape[1]):
            code = code * 100 + horses[:, column]
        return code
