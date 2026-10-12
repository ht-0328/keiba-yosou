"""第1段の条件のルール「多頭数で人気が割れている」（手順2の理論。docs/02）。"""

from __future__ import annotations

import pandas as pd

#: 多頭数とみなす出走頭数（事例で、16頭以上から帯が全体より集まった）。
CROWDED_FROM = 16
#: 使う列。
FIELD_SIZE, TOP3_SHARE = "出走頭数", "市場勝率の上位3頭の合計"


def crowded_split_score(races: pd.DataFrame) -> pd.Series:
    """多頭数（16頭以上）なら 1 を足し、そのうえで上位3頭の市場勝率の合計が小さい（人気が割れている）ほど高い点数。

    上位3頭の合計は 0〜1 なので、多頭数のレースは、どの多頭数でないレースよりも必ず上に来る。
    """
    crowded = races[FIELD_SIZE].ge(CROWDED_FROM).astype(float)
    return crowded + (1.0 - races[TOP3_SHARE])
