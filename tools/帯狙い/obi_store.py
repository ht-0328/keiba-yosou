"""帯狙いの結果を reports/帯狙い/ に書く・読む。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

#: keiba-yosou のリポジトリ直下（tools/帯狙い/ から2つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: 既定の置き場所。JV-Data から作った値なので Git の対象外（reports/）に置く。
DEFAULT_FOLDER = _PROJECT_ROOT / "reports" / "帯狙い"


class ObiStore:
    """1日の帯狙いの結果（選んだレース・荒れそうなレースの順位・買い目）を、``<置き場所>/<開催日>.json`` に書く・読む。"""

    def __init__(self, folder: Path = DEFAULT_FOLDER) -> None:
        self._folder = Path(folder)

    @property
    def folder(self) -> Path:
        return self._folder

    def save(self, day: date, result: dict[str, Any]) -> Path:
        path = self._path(day)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    def load(self, day: date) -> dict[str, Any] | None:
        """書いてある結果。無ければ None。"""
        path = self._path(day)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _path(self, day: date) -> Path:
        return self._folder / f"{day.isoformat()}.json"
