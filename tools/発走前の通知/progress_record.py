"""通知の進み具合（画面に出す行）を、ファイルにも残す。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TextIO


class ProgressRecord:
    """画面への出力をそのまま流しながら、同じ行を時刻つきでファイルに足す。
    タスクスケジューラから動かすと、窓が閉じたあとに画面の出力が残らず、途中で止まった理由が分からなくなるため。
    ファイルに書けなくても通知は止めない。"""

    def __init__(self, stream: TextIO, path: Path, now=datetime.now) -> None:
        self._stream = stream
        self._path = path
        self._now = now
        self._line_start = True

    def write(self, text: str) -> int:
        written = self._stream.write(text)
        self._append(text)
        return written

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name: str):
        return getattr(self._stream, name)

    def _append(self, text: str) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as file:
                file.write(self._stamped(text))
        except OSError:
            return

    def _stamped(self, text: str) -> str:
        """行の頭に時刻を付ける。"""
        parts = []
        for piece in text.splitlines(keepends=True):
            head = f"{self._now():%H:%M:%S} " if self._line_start else ""
            parts.append(head + piece)
            self._line_start = piece.endswith("\n")
        return "".join(parts)
