"""予想の結果を reports/今週の予想/ に書く・読む。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: keiba-yosou のリポジトリ直下（tools/今週の予想/ から2つ上）。
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
#: 既定の置き場所。JV-Data から作った値なので Git の対象外（reports/）に置く。
DEFAULT_FOLDER = _PROJECT_ROOT / "reports" / "今週の予想"


class ForecastStore:
    """1レースの予想の結果（``RaceForecaster.forecast`` の辞書）を、``<置き場所>/<開催日>/<rid>.json`` に書く・読む。

    画面は、ここに書いてある結果を読んで見せる（予想には1レース数十秒かかるので、先にまとめて作っておく）。
    """

    def __init__(self, folder: Path = DEFAULT_FOLDER) -> None:
        self._folder = Path(folder)

    def save(self, forecast: dict[str, Any]) -> Path:
        path = self._path(forecast["rid"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(forecast, ensure_ascii=False, indent=1), encoding="utf-8")
        return path

    def load(self, race_id: str) -> dict[str, Any] | None:
        """書いてある結果。無ければ None。"""
        path = self._path(race_id)
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def saved_at(self, race_id: str) -> str | None:
        """書いてある結果を作った時刻。無ければ None。"""
        forecast = self.load(race_id)
        return forecast.get("made_at") if forecast else None

    def _path(self, race_id: str) -> Path:
        day = f"{race_id[:4]}-{race_id[4:6]}-{race_id[6:8]}"
        return self._folder / day / f"{race_id}.json"
