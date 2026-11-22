"""1レースの 馬番 → 騎手名 を元DB から読む（表の画像の騎手の列のため）。地方（nvdata-store）と中央（jvdata-store）。"""

from __future__ import annotations

from pathlib import Path

from 共通 import db

from 発走前の通知.race_jockey_repository import RaceJockeyRepository


class RaceJockeys:
    """``default`` はどちらの元DB か（既定は地方）。DB は読むたびに開いてすぐ閉じる（取り込みの邪魔をしない）。"""

    def __init__(self, db_path: str | Path | None = None, default: db.DatabaseDefault = db.LOCAL) -> None:
        self._db_path = db_path
        self._default = default

    def read(self, rid: str) -> dict[int, str]:
        with db.open_db(self._db_path, default=self._default) as con:
            return RaceJockeyRepository(con).read(rid)
