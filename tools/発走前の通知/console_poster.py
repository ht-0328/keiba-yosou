"""Discord に投稿する代わりに、標準出力に出す（--dry-run）。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO


class ConsolePoster:
    def __init__(self, out: TextIO | None = None) -> None:
        self._out = out or sys.stdout

    def post(self, text: str, attachment: Path | None = None) -> None:
        print(text, file=self._out)
        if attachment is not None:
            print(f"（添付: {attachment}）", file=self._out)
        print(file=self._out, flush=True)
