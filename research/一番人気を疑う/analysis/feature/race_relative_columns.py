"""数値の材料を、同じレースの馬と比べた値にした列を足す。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class RaceRelativeColumns:
    """数値の材料それぞれに、「レース内の差」（平均との差を標準偏差で割った値）と「レース内の順位」（0〜1）を足す。

    モデルは1頭ずつ見るので、比べた値を渡さないと、そのメンバーの中で強いかが分からない。
    例: 近5走の平均着順が 3.0 でも、ほかの馬が 2.0 ばかりなら、このレースでは下のほうである。
    全員が同じ値のレースでは、差は欠損にする（比べようがないため）。
    """

    def add(self, frame: pd.DataFrame, columns: list[str]) -> list[str]:
        """``frame`` に列を足し、足した列の名前を返す。数値でない列は飛ばす。"""
        numeric = [column for column in columns if pd.api.types.is_numeric_dtype(frame[column])]
        by_race = frame.groupby("レースID")
        added: list[str] = []
        for column in numeric:
            spread = by_race[column].transform("std").replace(0, np.nan)
            frame[f"{column}（レース内の差）"] = (frame[column] - by_race[column].transform("mean")) / spread
            frame[f"{column}（レース内の順位）"] = by_race[column].rank(pct=True)
            added += [f"{column}（レース内の差）", f"{column}（レース内の順位）"]
        return added
