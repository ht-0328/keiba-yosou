"""地方の1レースの予想（predict の JSON）の置き場所と読み書きの時刻。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from 発走前の通知.folders import LOCAL_FOLDER


class LocalForecastStore:
    """``reports/発走前の通知/地方/<開催日>/<rid>.json``。書くのは地方の predict（``--out``）で、ここは場所と読み出しだけ。
    通知に添付する表の画像は同じフォルダの ``<rid>.png``。"""

    def __init__(self, folder: Path = LOCAL_FOLDER) -> None:
        self._folder = folder

    def path(self, rid: str) -> Path:
        return self._folder / f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}" / f"{rid}.json"

    def image_path(self, rid: str) -> Path:
        return self.path(rid).with_suffix(".png")

    def saved_at(self, rid: str) -> datetime | None:
        """ファイルの更新時刻（無ければ None）。予想し直せたかの確認に使う。"""
        path = self.path(rid)
        return datetime.fromtimestamp(path.stat().st_mtime) if path.is_file() else None

    def load(self, rid: str) -> dict[str, Any] | None:
        path = self.path(rid)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
