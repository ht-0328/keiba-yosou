"""目的変数を付けるクラスに共通の決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class TargetLabeler(Protocol):
    """目的変数の付け方（予想ごとに違う。設計書 10）。

    この決まりを守るクラスを ``DatasetBuilder`` に渡すと、``DatasetBuilder`` は「何を当てる予想か」を知らずに済む。
    """

    @property
    def label_name(self) -> str:
        """モデルに当てさせる列の名前（``build`` が作る表の列の1つ）。"""
        ...

    def build(self, samples: pd.DataFrame) -> pd.DataFrame:
        """目的変数の表。行の並びと index は ``samples`` と同じ。"""
        ...
