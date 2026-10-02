"""特徴量を、同じレースの出走馬の中での位置に直す。"""

from __future__ import annotations

import pandas as pd


class RaceRelative:
    """指定した列ごとに、レース内の順位（大きいほど良い列は大きい順）・最良との差・偏差を足す。

    1頭ずつ当てるモデルは、相手が誰かを知らない。「このメンバーの中で何番目か」を渡すと、相手の強さを考えられる。
    例: 指数が 82 で、レースの最高が 86・平均 78・標準偏差 4 なら、最良との差 −4、偏差 1.0。
    ``higher_is_better`` が偽の列（着順・着差など）は、小さいほど良いとして順位と最良を取る。
    """

    def add(self, table: pd.DataFrame, columns: dict[str, bool]) -> pd.DataFrame:
        race = table["race_id"]
        added = {}
        for column, higher_is_better in columns.items():
            grouped = table[column].groupby(race)
            best = grouped.transform("max") if higher_is_better else grouped.transform("min")
            added[f"{column}_順位"] = grouped.rank(ascending=not higher_is_better, method="min")
            added[f"{column}_最良との差"] = table[column] - best
            added[f"{column}_偏差"] = (table[column] - grouped.transform("mean")) / grouped.transform("std")
        return table.assign(**added)
