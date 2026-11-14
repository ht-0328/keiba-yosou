"""比べる相手（今の重賞の買い方）: 消を除いて複勝の期待値の高い順に2点を、セル × 開催日に数える。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from 全レース全券種の買い方.analysis.day_table import DayTable

#: 今のノルマ参加（重賞）の点数。
POINTS = 2


class PlaceBaseline:
    """印を付けた表（1行 = 1頭。列 race_id・race_date・mark・place_value・place_payout）と重賞のセルの表（``GradedCells.build``）から、
    重賞ごとに消を除いた複勝の期待値の上位 ``POINTS`` 頭の複勝を1点 100円で買ったときの、配列 [セル, 開催日, 4] を作る（docs/01 の 5）。
    払戻は 100円あたり（印を付けた表の ``place_payout`` のまま）。"""

    def build(self, marked: pd.DataFrame, cells_table: pd.DataFrame, cells: Sequence[str], days: Sequence[pd.Timestamp]) -> np.ndarray:
        horses = marked[["race_id", "mark", "place_value", "place_payout"]].assign(race_id=lambda frame: frame["race_id"].astype(str))
        horses = horses[(horses["mark"] != "消") & horses["place_value"].notna()]
        horses = horses.merge(cells_table[["race_id", "race_date", "cell"]], on="race_id", how="inner")
        top = horses.sort_values(["race_id", "place_value"], ascending=[True, False]).groupby("race_id").head(POINTS)
        top = top.assign(payout=top["place_payout"].fillna(0.0).astype(float), race_date=pd.to_datetime(top["race_date"])).reset_index(drop=True)
        table = DayTable(cells, days)
        table.add(top, np.ones(len(top), dtype=bool))
        return table.values
