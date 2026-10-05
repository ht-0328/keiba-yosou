"""jvdata-store の画面に聞く部品（``StoreScreenProbe``）のテスト。小さな偽のサーバーで応答を作る。"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from 取得と予想の状況.store_screen_probe import StoreScreenProbe

#: 誰も聞いていないポート（接続できない）。
CLOSED_URL = "http://127.0.0.1:1/"


def fake_store(responses: dict[str, dict]):
    """``/api/info`` などに決まった JSON を返すサーバーを立てて、そのアドレスを返す。"""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: D401 テストの出力を汚さない
            pass

        def do_GET(self):
            body = json.dumps(responses.get(self.path, {"error": "not found"})).encode("utf-8")
            self.send_response(200 if self.path in responses else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def fetching():
    yield from fake_store({"/api/info": {"app": "jvdata-store", "db": "C:/x/jvdata.duckdb"},
                           "/api/task": {"running": True, "label": "速報の取得（2026-10-05）", "status": "running", "finished_at": None}})


@pytest.fixture
def other_app():
    yield from fake_store({"/api/info": {"app": "keiba-yosou", "db": "x"}})


def test_止まっていれば応答なし() -> None:
    screen = StoreScreenProbe(CLOSED_URL, timeout=0.5).probe()
    assert not screen.running and screen.error == "応答なし" and screen.describe().startswith("止まっている")


def test_取得中なら実行中の処理の名前が分かる(fetching: str) -> None:
    screen = StoreScreenProbe(fetching).probe()
    assert screen.running and screen.task_running and screen.task_label == "速報の取得（2026-10-05）"
    assert screen.describe() == "動いている。実行中: 速報の取得（2026-10-05）"


def test_別の画面が応えたら動いていないと見る(other_app: str) -> None:
    screen = StoreScreenProbe(other_app).probe()
    assert not screen.running and "keiba-yosou" in screen.error
