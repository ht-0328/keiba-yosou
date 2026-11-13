"""その日の WIN5（対象レース5つと発走時刻）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from 共通 import codes

#: rid の中の競馬場コードとレース番号の位置。
_VENUE = slice(8, 10)
_RACE_NO = slice(14, 16)


@dataclass(frozen=True)
class Win5Slot:
    """開催日・対象レース5つの rid（発売の順）・発走時刻（rid の順。レースの一覧に無ければ None）。"""

    day: str
    race_ids: tuple[str, ...]
    posts: tuple[datetime | None, ...]

    @property
    def first_post(self) -> datetime:
        """1レース目の発走時刻（無ければ、分かっている発走時刻のうちいちばん早いもの）。"""
        return self.posts[0] or min(post for post in self.posts if post is not None)

    def due_at(self, minutes_before: int) -> datetime:
        """取り込みと予想を始める時刻（1レース目の発走の ``minutes_before`` 分前）。"""
        return self.first_post - timedelta(minutes=minutes_before)

    @property
    def label(self) -> str:
        """記録と失敗の知らせに使う短い名前（例 ``WIN5（1レース目 東京10R 14:50 発走）``）。"""
        first = self.race_ids[0]
        return f"WIN5（1レース目 {codes.venue_name(first[_VENUE])}{int(first[_RACE_NO])}R {self.first_post:%H:%M} 発走）"
