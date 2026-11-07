"""1レースの 馬番 → 枠番 を元DB から読む（表の画像で馬番を枠の色にするため）。地方（nvdata-store）と中央（jvdata-store）。"""

from __future__ import annotations

from pathlib import Path

from 共通 import db

from 地方の推奨買目.repository.local_frame_repository import LocalFrameRepository


class RaceFrames:
    """出走馬の表（se）は中央と地方で同じ列なので、同じ ``LocalFrameRepository`` で読む。``default`` はどちらの元DB か（既定は地方）。
    DB は読むたびに開いてすぐ閉じる（取り込みの邪魔をしない）。"""

    def __init__(self, db_path: str | Path | None = None, default: db.DatabaseDefault = db.LOCAL) -> None:
        self._db_path = db_path
        self._default = default

    def read(self, rid: str) -> dict[int, int]:
        with db.open_db(self._db_path, default=self._default) as con:
            return LocalFrameRepository(con).read(rid)
