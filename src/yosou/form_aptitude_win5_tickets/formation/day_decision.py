"""その日の WIN5 を買うかどうか。"""

from __future__ import annotations

from enum import Enum


class DayDecision(Enum):
    """買う（日の期待値が買う日の線以上）か、見送り（線未満。買い目と当たる確率は同じ形で出す）。"""

    BUY = "買う"
    SKIP = "見送り"

    @property
    def label(self) -> str:
        return self.value
