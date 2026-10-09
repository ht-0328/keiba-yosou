"""出走ごとに、同じ馬の前走（この DB にある中央のレースで、1つ前に出走したレース）の値を付ける。"""

from __future__ import annotations

import pandas as pd


class ReferenceHistory:
    """``prev_finish``（前走の確定着順）・``prev_popularity``（前走の単勝人気）・``interval_days``（前走からの日数）・
    ``prev_distance``（前走の距離 m。芝ダや障害を問わない）を付ける。

    前走は、この DB にある中央の確定成績のうち、同じ馬が出走した1つ前のレース（出走取消・除外のレースは出走していないので
    前走に数えない）。DB の最初のころは、それより前の出走が DB に無いので、前走なしになる馬が多い。
    数える期間より前の出走も前走に使うので、期間で絞る前の、全部の出走を渡す。
    """

    def add(self, started: pd.DataFrame) -> pd.DataFrame:
        ordered = started.sort_values(["horse_id", "race_day", "rid"], kind="stable")
        previous = ordered.groupby("horse_id", sort=False)[["placing", "popularity", "day", "distance"]].shift(1)
        return ordered.assign(
            prev_finish=previous["placing"], prev_popularity=previous["popularity"],
            interval_days=(ordered["day"] - previous["day"]).dt.days, prev_distance=previous["distance"],
        ).sort_index()
