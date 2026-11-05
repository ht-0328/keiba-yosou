"""1レースの 馬番 → 枠番 を地方の元DB から読む（表の画像で馬番を枠の色にするため）。"""

from __future__ import annotations

from pathlib import Path

from 共通 import db

from 地方の推奨買目.repository.local_frame_repository import LocalFrameRepository


class LocalFrames:
    """DB は読むたびに開いてすぐ閉じる（nvdata-store の取り込みの邪魔をしない）。"""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = db_path

    def read(self, rid: str) -> dict[int, int]:
        with db.open_db(self._db_path, default=db.LOCAL) as con:
            return LocalFrameRepository(con).read(rid)
