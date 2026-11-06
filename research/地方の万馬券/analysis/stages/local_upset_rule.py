"""地方の券種ごとの荒れ具合の線引き。本番の予想 ``yosou.local_upset_level`` に移した。ここからは同じ名前で使える。"""

from __future__ import annotations

from yosou.local_upset_level.dataset import LOCAL_THRESHOLDS, LocalUpsetRule

__all__ = ["LOCAL_THRESHOLDS", "LocalUpsetRule"]
