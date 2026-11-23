"""地方の1レースの予想（predict の JSON）の置き場所と読み書きの時刻。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from 発走前の通知.folders import LOCAL_FOLDER


class LocalForecastStore:
    """``reports/発走前の通知/地方/<開催日>/<rid>.json``。書くのは地方の predict（``--out``）で、ここは場所と読み出しだけ。
    通知に添付する表の画像は同じフォルダの ``<rid>.png``、券種ごとの中荒れ以上の確率（通知のときの推奨買目を作り直す研究の確かめが読む）は ``<rid>.荒れ具合.json``、
    直前の買い目（道具「地方の直前の買い目」）は ``<rid>.直前.json``、高知ファイナルの買い目（道具「高知ファイナルの買い目」。高知の最終レースだけ）は ``<rid>.高知ファイナル.json``、その材料の時系列オッズは開催日ごとの ``時系列オッズ.duckdb``
    （元DB とは別のファイル。発走前に nvstore が 0B41 を取り込む）。"""

    def __init__(self, folder: Path = LOCAL_FOLDER) -> None:
        self._folder = folder

    def path(self, rid: str) -> Path:
        return self._folder / f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}" / f"{rid}.json"

    def image_path(self, rid: str) -> Path:
        return self.path(rid).with_suffix(".png")

    def upset_path(self, rid: str) -> Path:
        return self.path(rid).with_name(f"{rid}.荒れ具合.json")

    def late_path(self, rid: str) -> Path:
        return self.path(rid).with_name(f"{rid}.直前.json")

    def kochi_final_path(self, rid: str) -> Path:
        return self.path(rid).with_name(f"{rid}.高知ファイナル.json")

    def odds_history_path(self, rid: str) -> Path:
        return self.path(rid).with_name("時系列オッズ.duckdb")

    def saved_at(self, rid: str) -> datetime | None:
        """ファイルの更新時刻（無ければ None）。予想し直せたかの確認に使う。"""
        path = self.path(rid)
        return datetime.fromtimestamp(path.stat().st_mtime) if path.is_file() else None

    def load(self, rid: str) -> dict[str, Any] | None:
        path = self.path(rid)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
