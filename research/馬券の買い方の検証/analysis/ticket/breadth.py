"""買い方の広さ（広め・少点数）。"""

from __future__ import annotations

from enum import Enum


class Breadth(Enum):
    """買い方が広め（点数を多く。荒れるレース用）か、少点数（自信のあるレース用）か。値は人が読む名前。"""

    WIDE = "広め"
    NARROW = "少点数"

    @property
    def label(self) -> str:
        return self.value
