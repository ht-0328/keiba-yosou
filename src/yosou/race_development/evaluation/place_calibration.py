"""3着以内の確率の、帯ごとの実際の割合。"""

from __future__ import annotations

import pandas as pd

from ..dataset import label_names as names

#: 確率の帯の区切り。
BANDS: tuple[float, ...] = (0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0)
#: 入力の列（1行 = 1頭）。Harville の式で出した3着以内の確率。
TOP3_PROBABILITY = "p_top3"


class PlaceCalibration:
    """「3着以内の確率 0.3〜0.4」と出した馬が、実際に何割3着以内だったかを、帯ごとに出す（設計書 16 の 2）。

    Harville の式の偏り（強い馬の 2着・3着の確率が高く出すぎる）が、ならしの指数 λ で直りきっているかを見る。
    """

    def table(self, horses: pd.DataFrame) -> pd.DataFrame:
        """``horses`` は列 ``p_top3``・``確定着順``。1行 = 1つの帯。"""
        usable = horses[horses[TOP3_PROBABILITY].notna()]
        band = pd.cut(usable[TOP3_PROBABILITY], list(BANDS), include_lowest=True)
        placed = usable[names.FINISH].le(3).astype("float64")
        grouped = pd.DataFrame({"帯": band, "p": usable[TOP3_PROBABILITY], "placed": placed}).groupby("帯", observed=True)
        return pd.DataFrame({
            "出した3着以内の確率の帯": [str(interval) for interval in grouped.size().index],
            "頭数": grouped.size().to_numpy(),
            "出した確率の平均": grouped["p"].mean().to_numpy(),
            "実際に3着以内だった割合": grouped["placed"].mean().to_numpy(),
        })
