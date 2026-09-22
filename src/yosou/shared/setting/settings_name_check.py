"""設定ファイルに書かれた名前を確かめる。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

#: 設定ファイルでは変えられない引数（目的関数）。変えると predict_proba が、目的変数が 1 になる確率を返さなくなる。
_FIXED_NAMES: frozenset[str] = frozenset({"objective", "loss_function"})


class SettingsNameCheck:
    """利用者の設定ファイルの名前が、初期値のファイルにあるかを確かめる（設計書 14 の「決まり」）。

    書き間違えた項目が、黙って無視されるのを防ぐ。
    """

    def __init__(self, defaults: Mapping[str, Any]) -> None:
        self._defaults = defaults

    def check(self, overrides: Mapping[str, Any], where: str) -> None:
        """``overrides`` の名前を全部確かめる。誤りがあれば ``ValueError``。``where`` は誤りの場所の説明。"""
        for name, value in overrides.items():
            self._check_one(name, value, f"{where} の {name}")

    def _check_one(self, name: str, value: Any, place: str) -> None:
        if name in _FIXED_NAMES:
            raise ValueError(f"目的関数は設定ファイルでは変えられません: {place}")
        if name not in self._defaults:
            known_names = ", ".join(self._defaults)
            raise ValueError(f"知らない設定の名前です: {place}（書ける名前: {known_names}）")
        default = self._defaults[name]
        if not isinstance(default, Mapping):
            return
        if not isinstance(value, Mapping):
            raise ValueError(f"[{name}] は表（[ ] の見出し）で書いてください: {place}")
        SettingsNameCheck(default).check(value, place)
