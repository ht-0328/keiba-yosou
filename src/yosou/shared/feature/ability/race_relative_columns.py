"""列を、同じレースの出走馬の中での位置に直す。"""

from __future__ import annotations

import pandas as pd

from .ability_columns import RELATIVE_COLUMNS


class RaceRelativeColumns:
    """``RELATIVE_COLUMNS`` の列ごとに、レース内の順位（良い順）・最良との差・偏差を作る。

    1頭ずつ当てるモデルは、相手が誰かを知らない。「このメンバーの中で何番目か」を渡すと、相手の強さを考えられる。
    例: 指数が 82 で、レースの最高が 86・平均 78・標準偏差 4 なら、最良との差 −4、偏差 1.0。
    大きいほど良い列でない列（着差・上がりの順位など）は、小さいほど良いとして順位と最良を取る。
    """

    def build(self, table: pd.DataFrame) -> pd.DataFrame:
        """列は ``relative_columns()`` の順（ability_columns.py）。行の並びと index は ``table`` と同じ。"""
        race = table["race_id"]
        added: dict[str, pd.Series] = {}
        for column, higher_is_better in RELATIVE_COLUMNS.items():
            values = pd.to_numeric(table[column], errors="coerce").astype(float)
            grouped = values.groupby(race)
            best = grouped.transform("max") if higher_is_better else grouped.transform("min")
            added[f"{column}_順位"] = grouped.rank(ascending=not higher_is_better, method="min")
            added[f"{column}_最良との差"] = values - best
            added[f"{column}_偏差"] = (values - grouped.transform("mean")) / grouped.transform("std")
        return pd.DataFrame(added, index=table.index)
