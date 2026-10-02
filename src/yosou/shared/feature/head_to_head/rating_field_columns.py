"""レーティングを、同じレースの出走馬の中での位置に直す。"""

from __future__ import annotations

import pandas as pd

from .head_to_head_columns import FIELD_GAP, FIELD_RANK, FIELD_Z


class RatingFieldColumns:
    """同じレースの出走馬の中での、レーティングの順位（高い順。同じ値は同じ順位）・偏差・平均との差を作る。

    1頭ずつ当てるモデルは相手が誰かを知らないので、「このメンバーの中で何番目か」を列にしておく（まとまり G・M と同じ考え）。
    例: 1540 の馬が、レースの平均 1500・標準偏差 20 なら、平均との差 +40、偏差 2.0。1頭立てや、全頭が同じ値なら偏差は欠損値。
    ``race_ids`` は出走の行ごとのレースID、``ratings`` は同じ並びのレーティング。行の並びと index は ``ratings`` と同じ。
    """

    def build(self, race_ids: pd.Series, ratings: pd.Series) -> pd.DataFrame:
        grouped = ratings.groupby(race_ids.to_numpy())
        gap = ratings - grouped.transform("mean")
        return pd.DataFrame({
            FIELD_RANK: grouped.rank(ascending=False, method="min"),
            FIELD_Z: gap / grouped.transform("std"),
            FIELD_GAP: gap,
        }, index=ratings.index)
