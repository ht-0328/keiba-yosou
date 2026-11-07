"""DiscordWebhook（投稿）のテスト。ウェブフックには送らず、つなぎ（opener）を差し替える。"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

import pytest

from 発走前の通知.discord_webhook import DiscordWebhook
from 発走前の通知.message_splitter import MessageSplitter

URL = "https://example.invalid/api/webhooks/1/x"


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self) -> bytes:
        return b""


class _Opener:
    """送られた Request を覚える。``failures`` に入れた HTTPError を先頭から順に起こす。"""

    def __init__(self, failures: list[urllib.error.HTTPError] | None = None) -> None:
        self.requests: list[urllib.request.Request] = []
        self._failures = list(failures or [])

    def __call__(self, request: urllib.request.Request, timeout: int) -> _Response:
        self.requests.append(request)
        if self._failures:
            raise self._failures.pop(0)
        return _Response()


def _http_error(code: int, retry_after: str | None = None) -> urllib.error.HTTPError:
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return urllib.error.HTTPError(URL, code, "error", headers, io.BytesIO(b'{"message": "no"}'))


def test_短い文は1回のJSONで投稿し通知は鳴らさない() -> None:
    opener = _Opener()
    DiscordWebhook(URL, opener=opener).post("印の文 @everyone")
    (request,) = opener.requests
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data.decode("utf-8")) == {"content": "印の文 @everyone", "allowed_mentions": {"parse": []}}


def test_長い文は分けて順に投稿し添付は最後に付ける(tmp_path: Path) -> None:
    attachment = tmp_path / "根拠.md"
    attachment.write_text("# 全頭", encoding="utf-8")
    opener = _Opener()
    DiscordWebhook(URL, splitter=MessageSplitter(5), opener=opener).post("aaa\nbbb\nccc", [attachment])
    assert [json.loads(r.data.decode("utf-8"))["content"] for r in opener.requests[:1]] == ["aaa"]
    assert len(opener.requests) == 3
    last = opener.requests[-1]
    assert last.get_header("Content-type").startswith("multipart/form-data; boundary=")
    assert 'filename="根拠.md"'.encode("utf-8") in last.data
    assert b'name="payload_json"' in last.data
    assert "# 全頭".encode("utf-8") in last.data


def test_添付が2つなら_files_0_と_files_1_で1回に付ける(tmp_path: Path) -> None:
    image, reasons = tmp_path / "表.png", tmp_path / "根拠.md"
    image.write_bytes(b"PNG")
    reasons.write_text("# 全頭", encoding="utf-8")
    opener = _Opener()
    DiscordWebhook(URL, opener=opener).post("文", (image, reasons))
    (request,) = opener.requests
    assert 'name="files[0]"; filename="表.png"'.encode("utf-8") in request.data
    assert 'name="files[1]"; filename="根拠.md"'.encode("utf-8") in request.data
    assert b"Content-Type: image/png" in request.data and b"Content-Type: text/markdown" in request.data


def test_多すぎると言われたら待って1回やり直す() -> None:
    opener = _Opener([_http_error(429, "1.5")])
    waits: list[float] = []
    DiscordWebhook(URL, opener=opener, sleep=waits.append).post("文")
    assert waits == [1.5]
    assert len(opener.requests) == 2


def test_それ以外の失敗は理由つきで止まる() -> None:
    opener = _Opener([_http_error(400)])
    with pytest.raises(RuntimeError, match="HTTP 400"):
        DiscordWebhook(URL, opener=opener).post("文")
