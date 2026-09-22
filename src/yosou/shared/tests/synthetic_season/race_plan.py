"""レース1つの条件。"""

from __future__ import annotations

from dataclasses import dataclass

#: トラックコード。11 = 芝・左、23 = ダート・左、54 = 障害・芝。
TURF_TRACK, DIRT_TRACK, JUMP_TRACK = "11", "23", "54"


@dataclass(frozen=True)
class RacePlan:
    """レース1つの条件。``base_time`` は1着の走破タイム（``1340`` = 1分34秒0）。"""

    race_no: str
    track_code: str
    distance_m: int
    base_time: int

    @property
    def is_dirt(self) -> bool:
        return self.track_code == DIRT_TRACK

    @property
    def is_jump(self) -> bool:
        return self.track_code == JUMP_TRACK

    @property
    def ck_surface(self) -> str:
        """出走別着度数の欄の名前での、芝ダの書き方。"""
        return "ダ" if self.is_dirt else "芝"
