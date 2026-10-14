"""とっておいた表の隣の ``stamp.json``（元DB の印と、表の材料の最後の日）を読む・書く。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

#: 印のファイルの名前。
STAMP_FILE = "stamp.json"


class StampFile:
    """とっておいた表のフォルダの ``stamp.json`` を読む・書く。

    読むときは、表のファイル（``table_files``）がそろっていなければ None（表が無ければ、印があっても使えない）。
    書くときは、元DB の印（``DbStamp``）に、表の材料の最後の日 ``as_of`` を添える。
    """

    def __init__(self, folder: Path, table_files: tuple[str, ...]) -> None:
        self._folder = Path(folder)
        self._table_files = table_files

    def read(self) -> dict[str, object] | None:
        """とっておいた元DB の印（``db``・``mtime``）。印か表のファイルが無ければ None。"""
        path = self._folder / STAMP_FILE
        if not path.exists() or not all((self._folder / name).exists() for name in self._table_files):
            return None
        saved = json.loads(path.read_text(encoding="utf-8"))
        return {"db": saved.get("db"), "mtime": saved.get("mtime")}

    def write(self, stamp: dict[str, object], as_of: date | None) -> None:
        """元DB の印と、表の材料の最後の日を書く。"""
        self._folder.mkdir(parents=True, exist_ok=True)
        as_of_text = None if as_of is None else f"{as_of:%Y-%m-%d}"
        (self._folder / STAMP_FILE).write_text(json.dumps({**stamp, "as_of": as_of_text}, ensure_ascii=False, indent=2), encoding="utf-8")
