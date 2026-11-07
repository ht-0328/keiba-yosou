"""通知の文に馬場の傾向の行を出す部品の形（本番は ``TrackTendencies``。テストでは偽物を渡す）。"""

from __future__ import annotations

from typing import Protocol

from 発走前の通知.track_tendency import TrackTendency


class Tendencies(Protocol):
    def of(self, rid: str, venue: str) -> TrackTendency | None: ...
