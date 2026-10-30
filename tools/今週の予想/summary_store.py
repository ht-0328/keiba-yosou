"""開催日ごとの予想のまとめ（Markdown）を、今週の予想の結果と一緒に保存する。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from 今週の予想.forecast_store import ForecastStore

#: 1日のまとめのファイル名。
SUMMARY_FILE = "まとめ.md"


class SummaryStore:
    """1開催日のまとめ（``DaySummary`` が作る Markdown）を ``<置き場所>/<開催日>/まとめ.md`` に書く・読む。"""

    def __init__(self, forecasts: ForecastStore) -> None:
        self._forecasts = forecasts

    def path(self, day: date) -> Path:
        return self._forecasts.folder / day.isoformat() / SUMMARY_FILE

    def save(self, day: date, text: str) -> Path:
        path = self.path(day)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def load(self, day: date) -> str | None:
        path = self.path(day)
        return path.read_text(encoding="utf-8") if path.is_file() else None
