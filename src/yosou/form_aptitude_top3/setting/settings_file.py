"""TOML の設定ファイルを読む。"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


class SettingsFile:
    """TOML の設定ファイル1つ。"""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def read(self) -> dict[str, Any]:
        """ファイルの中身を辞書で返す。無ければ ``FileNotFoundError``、TOML として読めなければ ``ValueError``。"""
        if not self._path.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {self._path}")
        try:
            return tomllib.loads(self._path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            raise ValueError(f"設定ファイルを読めません（{self._path}）: {error}") from None
