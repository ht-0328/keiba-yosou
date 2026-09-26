"""同じレースの馬どうしで比べる特徴量のまとまりのクラスに共通の決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class FieldFeatureGroup(Protocol):
    """同じレースの馬どうしで比べて作るまとまり1つ（手本の G、展開の L・O）。

    ほかのまとまりの特徴量を、同じレースの全頭で比べるので、ほかのまとまりを作ったあとに呼ぶ。
    """

    def build(self, entries: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """``features`` は、``entries`` と同じ行の並びの、ほかのまとまり（比べるまとまり以外）の特徴量。
        列 = そのまとまりの特徴量。行の並びと index は ``entries`` と同じ。
        """
        ...
