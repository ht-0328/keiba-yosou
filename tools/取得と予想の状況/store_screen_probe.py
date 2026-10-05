"""取得の画面（jvdata-store・nvdata-store のサーバー）に、動いているか・何を実行中かを聞く。"""

from __future__ import annotations

import json
from typing import Any
from urllib.request import urlopen

from 取得と予想の状況.store_screen import StoreScreen

#: jvdata-store（中央）の画面の既定のアドレスと、``/api/info`` が名乗る名前（``jvstore serve`` の既定のポート 8766）。
JRA_STORE_URL = "http://127.0.0.1:8766/"
JRA_STORE_APP = "jvdata-store"
#: nvdata-store（地方）の画面の既定のアドレスと名前（``nvstore serve`` の既定のポート 8768）。
LOCAL_STORE_URL = "http://127.0.0.1:8768/"
LOCAL_STORE_APP = "nvdata-store"
#: 応答を待つ上限（秒）。同じ PC の画面なので、すぐ応えなければ止まっていると見る。
DEFAULT_TIMEOUT_SECONDS = 1.0


class StoreScreenProbe:
    """``/api/info`` と ``/api/task`` を読んで ``StoreScreen`` にする。応えなければ「止まっている」。

    ``app`` は相手が名乗るはずの名前。同じポートに別の画面がいることがあるので確かめる。
    """

    def __init__(self, url: str = JRA_STORE_URL, app: str = JRA_STORE_APP, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._url = url if url.endswith("/") else url + "/"
        self._app = app
        self._timeout = timeout

    def probe(self) -> StoreScreen:
        info = self._get("api/info")
        if info is None:
            return StoreScreen(name=self._app, url=self._url, running=False, error="応答なし")
        app = str(info.get("app", ""))
        if app != self._app:
            return StoreScreen(name=self._app, url=self._url, running=False, app=app, error=f"別の画面（{app or '不明'}）が応えた")
        task = self._get("api/task") or {}
        return StoreScreen(
            name=self._app, url=self._url, running=True, app=app, db=str(info.get("db", "")), task_label=str(task.get("label", "")),
            task_status=str(task.get("status", "")), task_running=bool(task.get("running")), finished_at=task.get("finished_at"),
        )

    def _get(self, path: str) -> dict[str, Any] | None:
        """JSON を読む。接続できない・JSON でない・辞書でないなら None。"""
        try:
            data = self._fetch_json(path)
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _fetch_json(self, path: str) -> Any:
        with urlopen(self._url + path, timeout=self._timeout) as response:
            return json.load(response)
