"""G. 同じレースの馬との比較（4個）。"""

from __future__ import annotations

import pandas as pd

from ..value_types import as_numbers


class FieldComparisonFeatures:
    """G. 同じレースの馬との比較。このメンバーの中で強いかを、ほかの馬と比べた値にする。

    モデルはサンプルを1行ずつ見るので、比べた値を特徴量にしておかないと、メンバーの強さが分からない。
    ほかのまとまりの特徴量を比べるので、それらを作ったあとに呼ぶ。
    """

    def build(self, entries: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """``features`` は、``entries`` と同じ行の並びの、ほかのまとまりの特徴量。順位は、同じ値なら同じ順位。"""
        race = entries["race_id"]
        carried = as_numbers(features["斤量"])
        recent_margin = as_numbers(features["近5走の平均着差"])
        jockey_rate = as_numbers(features["騎手の近1年の3着以内の割合"])
        return pd.DataFrame({
            "逃げそうな馬の数": entries["lead_candidates"],
            "近5走の平均着差のレース内順位": recent_margin.groupby(race).rank(method="min"),
            "斤量とレースの平均との差": carried - carried.groupby(race).transform("mean"),
            "騎手の3着以内の割合のレース内順位": jockey_rate.groupby(race).rank(method="min", ascending=False),
        })
