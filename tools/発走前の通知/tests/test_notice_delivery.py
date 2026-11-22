"""NoticeDelivery（文を作って投稿する段）のテスト。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from 発走前の通知.notice_delivery import NoticeDelivery
from 発走前の通知.race_notice import RaceNotice


class _Poster:
    def __init__(self) -> None:
        self.posts: list[tuple[str, tuple]] = []

    def post(self, text: str, attachments=()) -> None:
        self.posts.append((text, tuple(attachments)))


def test_AIだけの予想を添付つきで先に投稿し_続けてAIとロジックの予想を別に投稿する() -> None:
    poster = _Poster()
    delivery = NoticeDelivery(poster, lambda: datetime(2026, 11, 28, 10), lambda seconds: None, lambda text: None)
    notice = RaceNotice("AI の予想", (Path("a.png"),), ("AI＋ロジック予想",))
    assert delivery.deliver("京都 1R", lambda: notice, datetime(2026, 11, 28, 11))
    assert poster.posts == [("AI の予想", (Path("a.png"),)), ("AI＋ロジック予想", ())]
