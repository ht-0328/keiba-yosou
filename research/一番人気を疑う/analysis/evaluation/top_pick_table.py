"""レースごとに◎と1番人気を横に並べた表を作る。"""

from __future__ import annotations

import pandas as pd

#: 1番人気の側の列に付ける印。
FAVORITE_SUFFIX = "_1番人気"


class TopPickTable:
    """予測の表（1行 = 1頭。``レースID``・``馬番``・``確定の単勝人気``・``3着以内``・``score``）から、1行 = 1レースの表を作る。

    ◎は ``score`` がいちばん高い馬。1番人気は確定の単勝人気が 1 の馬（同じ人気が2頭なら馬番の若いほう）。
    1番人気がいないレース（人気が付かなかったなど）は落とす。
    列は、◎の列（予測の表の列そのまま）と、1番人気の列（名前の後ろに ``_1番人気``）と、``疑った``（◎が1番人気でない）。
    """

    def build(self, predictions: pd.DataFrame) -> pd.DataFrame:
        top = predictions.loc[predictions.groupby("レースID")["score"].idxmax()].set_index("レースID")
        favorites = predictions[predictions["確定の単勝人気"] == 1].sort_values("馬番").drop_duplicates("レースID")
        races = top.join(favorites.set_index("レースID"), rsuffix=FAVORITE_SUFFIX, how="inner")
        races["疑った"] = races["馬番"] != races[f"馬番{FAVORITE_SUFFIX}"]
        return races
