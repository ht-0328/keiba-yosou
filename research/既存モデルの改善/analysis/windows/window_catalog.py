"""予想ごとに使う区切りの並び。"""

from __future__ import annotations

from .stakes_windows import STAKES_WINDOWS
from .test_window import TestWindow
from .test_windows import WINDOWS

#: 半年の区切り（``WINDOWS``）でなく、別の区切りを使う予想。
_WINDOWS_OF: dict[str, tuple[TestWindow, ...]] = {"stakes_tendency_top3": STAKES_WINDOWS}


def windows_of(model: str) -> tuple[TestWindow, ...]:
    """その予想の区切りの並び。重賞の予想は1年ずつの7つ、ほかは半年ずつの7つ。"""
    return _WINDOWS_OF.get(model, WINDOWS)
