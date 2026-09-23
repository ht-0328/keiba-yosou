"""毎週の選び方。"""

from __future__ import annotations

from enum import Enum


class WeeklyMode(Enum):
    """⑤⑥で、週ごとに上位 k レースを何で選ぶか。値は鍵に使う。"""

    UPSET = "upset"
    CONFIDENT = "conf"
    BOTH = "both"

    @property
    def label(self) -> str:
        return {WeeklyMode.UPSET: "荒れる", WeeklyMode.CONFIDENT: "自信", WeeklyMode.BOTH: "両方"}[self]

    @property
    def uses_upset(self) -> bool:
        return self in (WeeklyMode.UPSET, WeeklyMode.BOTH)

    @property
    def uses_confidence(self) -> bool:
        return self in (WeeklyMode.CONFIDENT, WeeklyMode.BOTH)
