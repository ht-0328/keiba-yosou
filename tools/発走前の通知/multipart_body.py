"""multipart/form-data の本文（欄と添付ファイル）を組む。"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence

#: 部品の区切り（CRLF）。
_CRLF = "\r\n"


class MultipartBody:
    def __init__(self, boundary: str | None = None) -> None:
        self._boundary = boundary or uuid.uuid4().hex

    @property
    def content_type(self) -> str:
        return f"multipart/form-data; boundary={self._boundary}"

    def encode(self, fields: Mapping[str, str], files: Sequence[tuple[str, str, bytes]]) -> bytes:
        """``fields`` は 欄の名前 → 値、``files`` は（欄の名前, ファイル名, 中身）。"""
        parts = [self._field(name, value) for name, value in fields.items()]
        parts += [self._file(name, filename, data) for name, filename, data in files]
        return b"".join(parts) + f"--{self._boundary}--{_CRLF}".encode("utf-8")

    def _field(self, name: str, value: str) -> bytes:
        head = f"--{self._boundary}{_CRLF}Content-Disposition: form-data; name=\"{name}\"{_CRLF}{_CRLF}"
        return f"{head}{value}{_CRLF}".encode("utf-8")

    def _file(self, name: str, filename: str, data: bytes) -> bytes:
        head = (f"--{self._boundary}{_CRLF}Content-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"{_CRLF}"
                f"Content-Type: application/octet-stream{_CRLF}{_CRLF}")
        return head.encode("utf-8") + data + _CRLF.encode("utf-8")
