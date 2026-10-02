"""スピード指数が、同じ馬の続けて走ったレースどうしでどれだけそろうか。"""

from __future__ import annotations

import pandas as pd

from 共通.ability import FIGURE

#: 続けて走ったとみなす、前の走からの日数の上限。
_MAX_DAYS = 180


class FigureConsistency:
    """``first``〜``last`` の開催日の走と、その馬の1つ前の走（180日以内）の、スピード指数の相関を出す。

    補正（馬場差・斤量・ペースなど）が、タイムのぶれ（その日の馬場や展開のせい）をうまく取り除くほど、同じ馬の
    続けた走どうしの指数はそろい、相関が上がる。例: 相関 0.60 → 0.65 なら、その補正でぶれが減った。
    """

    def score(self, runs: pd.DataFrame, first: str, last: str) -> dict[str, float]:
        ordered = runs.sort_values(["horse_id", "race_date", "race_id"], kind="stable")
        grouped = ordered.groupby("horse_id", sort=False)
        previous = grouped[FIGURE].shift()
        days = (ordered["race_date"] - grouped["race_date"].shift()).dt.days
        chosen = ordered["race_date"].between(pd.Timestamp(first), pd.Timestamp(last)) & (days <= _MAX_DAYS)
        pairs = pd.DataFrame({"now": ordered[FIGURE], "before": previous})[chosen].dropna()
        return {"組の数": len(pairs), "続けた走の相関": pairs["now"].corr(pairs["before"]),
                "指数の標準偏差": ordered.loc[chosen, FIGURE].std()}
