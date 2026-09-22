"""初期値に、利用者が書いた項目を重ねる。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SettingsOverlay:
    """初期値の設定に、利用者の設定ファイルに書かれた項目だけを重ねる。書かれなかった項目は初期値のまま。"""

    def __init__(self, defaults: Mapping[str, Any]) -> None:
        self._defaults = defaults

    def apply(self, overrides: Mapping[str, Any]) -> dict[str, Any]:
        """重ねた結果の辞書。表（``[lightgbm.params]`` など）の中は、項目ごとに重ねる。"""
        merged = dict(self._defaults)
        for name, value in overrides.items():
            merged[name] = self._merged_value(name, value)
        return merged

    def _merged_value(self, name: str, value: Any) -> Any:
        if not isinstance(value, Mapping):
            return value
        return SettingsOverlay(self._defaults[name]).apply(value)
