"""その日に発走する1レース（rid・場・R・レース名・発走時刻）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class ScheduledRace:
    rid: str
    venue: str
    number: int
    name: str
    #: 発走時刻（開催日つき）。
    post: datetime

    def due_at(self, minutes_before: int) -> datetime:
        """取り込みと予想を始める時刻（発走の ``minutes_before`` 分前）。"""
        return self.post - timedelta(minutes=minutes_before)

    @property
    def day(self) -> str:
        return self.post.date().isoformat()

    @property
    def label(self) -> str:
        """記録と失敗の知らせに使う短い名前（例 ``東京 11R 天皇賞（秋）（15:40 発走）``）。"""
        name = f" {self.name}" if self.name else ""
        return f"{self.venue} {self.number}R{name}（{self.post:%H:%M} 発走）"
