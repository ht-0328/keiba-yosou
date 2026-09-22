"""予測の結果を、区分（中穴・大穴）で絞る。"""

from __future__ import annotations

import pandas as pd

from .column_names import LONGSHOT_ZONE
from .longshot_zone import LongshotZone


class LongshotZoneFilter:
    """予測の結果（1行 = 穴馬1頭）を、指定された区分の行だけにする（設計書 05 の図2）。

    モデルは穴馬すべてに確率を出す。区分は、出力を絞るときにだけ使う（設計書 15 の 3）。
    """

    def apply(self, prediction: pd.DataFrame, zone: LongshotZone | None) -> pd.DataFrame:
        """``zone`` が None なら、そのまま返す。その区分の穴馬が1頭もいなければ ``LookupError``。"""
        if zone is None:
            return prediction
        chosen = prediction[prediction[LONGSHOT_ZONE] == zone.label]
        if chosen.empty:
            raise LookupError(f"{zone.label}の穴馬がいません（このレースの穴馬 {len(prediction)}頭に、{zone.label}はいません）")
        return chosen
