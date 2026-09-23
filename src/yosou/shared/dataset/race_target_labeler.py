"""レース単位の目的変数を付けるクラスに共通の決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class RaceTargetLabeler(Protocol):
    """レース単位の目的変数の付け方（荒れ具合の設計書 10）。目的変数の列は、複数あってよい（券種ごと など）。

    1頭ごとの ``TargetLabeler`` は列名が1つなので、レース単位の予想は、この決まりを ``RaceDatasetBuilder`` に渡す。
    """

    @property
    def label_names(self) -> tuple[str, ...]:
        """目的変数の列の名前の並び。最初の列が、既定でモデルに当てさせる列。"""
        ...

    def build(self, races: pd.DataFrame) -> pd.DataFrame:
        """目的変数の表（列は ``label_names``）。``races`` はレースごとの払戻（1行 = 1レース。index はレースID）で、
        行の並びと index は ``races`` と同じ。目的変数を付けられないレース（発売なし・不成立）は欠損値。
        """
        ...
