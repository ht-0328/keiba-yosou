"""Discord に投稿する代わりに、標準出力に出す（--dry-run）。"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO


class ConsolePoster:
    def __init__(self, out: TextIO | None = None) -> None:
        self._out = out or sys.stdout

    def post(self, text: str, attachments: Sequence[Path] = ()) -> None:
        print(text, file=self._out)
        for attachment in attachments:
            print(f"（添付: {attachment}）", file=self._out)
        print(file=self._out, flush=True)
