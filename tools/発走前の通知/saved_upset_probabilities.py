"""推奨買目の荒れ具合の条件（3連複）に、発走前の予想が書いておいた中荒れ以上の確率を渡す。"""

from __future__ import annotations

from collections.abc import Sequence

import duckdb

from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_upset_file import LocalUpsetFile


class SavedUpsetProbabilities:
    """推奨買目の ``UpsetSource`` と同じ形。荒れ具合の予想はここでは計算せず、``LocalForecastStore.upset_path`` のファイルを読むだけ
    （予想と同じプロセス・同じ接続で出してあるので、地方の全成績の事実表を作り直さずに済む）。接続は使わない。"""

    def __init__(self, store: LocalForecastStore | None = None, file: LocalUpsetFile | None = None) -> None:
        self._store = store or LocalForecastStore()
        self._file = file or LocalUpsetFile()

    def of(self, con: duckdb.DuckDBPyConnection, rid: str, tickets: Sequence[str]) -> dict[str, float]:
        return self._file.read(self._store.upset_path(rid), tickets)
