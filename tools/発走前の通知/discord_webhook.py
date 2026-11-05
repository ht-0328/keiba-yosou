"""Discord のウェブフックに、文（と添付ファイル）を投稿する。"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from 発走前の通知.message_splitter import MessageSplitter
from 発走前の通知.multipart_body import MultipartBody

#: 投稿が多すぎると言われた（HTTP 429）ときに、Retry-After が無ければ待つ秒数。
_RETRY_WAIT = 2.0
#: 1回の投稿の待ち時間の上限（秒）。
_TIMEOUT = 30
#: Discord に名乗る User-Agent（無いと拒まれることがある）。
_HEADERS = {"User-Agent": "keiba-yosou-race-notify/1.0"}
#: 投稿が多すぎるときの HTTP の状態。
_TOO_MANY_REQUESTS = 429


class DiscordWebhook:
    """長い文は ``MessageSplitter`` で上限以下に分けて順に投稿し、添付は最後の投稿に付ける。
    文の中の ``@everyone`` などは通知にしない（allowed_mentions を空にする）。
    投稿が多すぎると言われたら、言われた秒数だけ待って1回だけやり直す。それ以外の失敗は ``RuntimeError``。
    """

    def __init__(self, url: str, *, splitter: MessageSplitter | None = None,
                 opener: Callable[..., object] = urllib.request.urlopen, sleep: Callable[[float], None] = time.sleep) -> None:
        self._url = url
        self._splitter = splitter or MessageSplitter()
        self._opener = opener
        self._sleep = sleep

    def post(self, text: str, attachment: Path | None = None) -> None:
        chunks = self._splitter.split(text)
        last = len(chunks) - 1
        for index, chunk in enumerate(chunks):
            self._send(chunk, attachment if index == last else None)

    def _send(self, content: str, attachment: Path | None) -> None:
        try:
            self._deliver(content, attachment)
        except urllib.error.HTTPError as error:
            self._retry_if_too_many(error, content, attachment)

    def _retry_if_too_many(self, error: urllib.error.HTTPError, content: str, attachment: Path | None) -> None:
        if error.code != _TOO_MANY_REQUESTS:
            detail = error.read().decode("utf-8", errors="replace")[:200]
            raise RuntimeError(f"Discord への投稿に失敗しました（HTTP {error.code}: {detail}）") from error
        self._sleep(float(error.headers.get("Retry-After") or _RETRY_WAIT))
        self._deliver(content, attachment)

    def _deliver(self, content: str, attachment: Path | None) -> None:
        with self._opener(self._request(content, attachment), timeout=_TIMEOUT) as response:
            response.read()

    def _request(self, content: str, attachment: Path | None) -> urllib.request.Request:
        payload = json.dumps({"content": content, "allowed_mentions": {"parse": []}}, ensure_ascii=False)
        if attachment is None:
            return urllib.request.Request(self._url, data=payload.encode("utf-8"), method="POST",
                                          headers={**_HEADERS, "Content-Type": "application/json"})
        body = MultipartBody()
        data = body.encode({"payload_json": payload}, [("files[0]", attachment.name, attachment.read_bytes())])
        return urllib.request.Request(self._url, data=data, method="POST", headers={**_HEADERS, "Content-Type": body.content_type})
