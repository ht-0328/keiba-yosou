"""印を付けた表から、馬ごとの「位置」（◎ か、◎ を除いた確率の順位か、消か）を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 位置の列。◎ は 0、ほかは ◎ と消を除いた3着以内の確率の高い順（1 = ○、2 = ▲ …）、消は欠損値（買い目に入れない）。
POSITION = "pos"
COLUMNS: tuple[str, ...] = ("race_id", "horse_no", POSITION)
#: 確率の線で相手を決める型のための、レースごとの「◎・消を除いて3着以内の確率が線以上の馬の数」の列（線 → 列の名前）。
THRESHOLD_COLUMNS: dict[float, str] = {0.5: "n50", 0.25: "n25"}


class HorseSlots:
    """印を付けた表（1行 = 1頭。列 race_id・horse_no・mark・probability）から、馬ごとの位置を出す（docs/01 の 4）。

    位置は、型の「軸 K」と「相手 N」の判定に使う。軸の頭数 k・相手の頭数 n に対して、位置 p の馬は
    「p ≤ k − 1 なら軸、k − 1 < p ≤ k − 1 + n なら相手」。◎ は常に位置 0 で、○ は 1、▲ は 2（印の決め方と同じ順）、△ 以降も確率の順。
    消（危険な人気馬）は位置を持たない（軸にも相手にも入らない）。
    """

    def build(self, marked: pd.DataFrame) -> pd.DataFrame:
        table = marked[["race_id", "horse_no", "mark", "probability"]].copy()
        table["race_id"] = table["race_id"].astype(str)
        table["horse_no"] = table["horse_no"].astype(int)
        is_top = table["mark"] == "◎"
        is_out = table["mark"] == "消"
        others = table[~is_top & ~is_out].sort_values(["race_id", "probability", "horse_no"], ascending=[True, False, True])
        ranks = others.groupby("race_id").cumcount() + 1
        table[POSITION] = np.nan
        table.loc[is_top, POSITION] = 0.0
        table.loc[others.index, POSITION] = ranks.to_numpy(dtype=float)
        return table[list(COLUMNS)].reset_index(drop=True)

    def partner_counts(self, marked: pd.DataFrame) -> pd.DataFrame:
        """レースごとの、◎ と消を除いて3着以内の確率が線以上の馬の数（列 race_id と ``THRESHOLD_COLUMNS`` の列）。"""
        table = marked[["race_id", "mark", "probability"]].assign(race_id=lambda frame: frame["race_id"].astype(str))
        others = table[~table["mark"].isin(["◎", "消"])]
        counts = pd.DataFrame({"race_id": table["race_id"].drop_duplicates().to_numpy()})
        for threshold, column in THRESHOLD_COLUMNS.items():
            over = others[others["probability"] >= threshold].groupby("race_id").size().rename(column)
            counts = counts.merge(over, on="race_id", how="left")
            counts[column] = counts[column].fillna(0).astype(int)
        return counts
