"""区切り（半年ごと）。今のモデルの区切りごとの予測（研究「複勝以外の回収率100超」の predictions-2019から）と同じ15の区切り。"""

from __future__ import annotations

from 既存モデルの改善.analysis.windows.test_windows import WINDOWS as RECENT_WINDOWS
from 複勝以外の回収率100超.analysis.early_windows import EARLIEST_WINDOWS, EARLY_WINDOWS

#: 2019年前半〜2026年。各区切りは、その半年より前（2012年から）で学び、直前の半年で木を足すのを止め、その半年を予測する。
WINDOWS = (*EARLIEST_WINDOWS, *EARLY_WINDOWS, *RECENT_WINDOWS)


def window_named(name: str):
    for window in WINDOWS:
        if window.name == name:
            return window
    raise ValueError(f"知らない区切りです: {name}（{' / '.join(window.name for window in WINDOWS)}）")
