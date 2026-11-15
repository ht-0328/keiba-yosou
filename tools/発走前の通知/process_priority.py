"""通知のプロセスの優先度を「通常」に上げる（タスクスケジューラから動かすと「通常以下」で始まり、ほかのアプリに後回しにされるため）。"""

from __future__ import annotations

import sys
from collections.abc import Callable

#: Windows の「通常」の優先度（NORMAL_PRIORITY_CLASS）。
NORMAL_PRIORITY_CLASS = 0x00000020


def _raise_windows() -> bool:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # 引数と戻り値の型を決めておく（決めないと 64 ビットのハンドルが int に切られて、変えられない）。
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetPriorityClass.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel32.SetPriorityClass.restype = wintypes.BOOL
    return bool(kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), NORMAL_PRIORITY_CLASS))


def _nothing() -> bool:
    return True


class ProcessPriority:
    """今のプロセスの優先度を「通常」に上げる。

    タスクスケジューラのタスクは、既定で優先度「通常以下」で動く。そのままだと、予想の間にほかのアプリ（ブラウザやエディタ）が
    CPU を使うと予想が後回しにされ、バッテリーで動いているときは特に遅れて、発走に間に合わないことがあった。
    Windows では、優先度が「通常」のプロセスから始めたプロセス（uv・予想・速報の取り込み）も「通常」で動く。
    Windows 以外では何もしない（もとから通常で動く）。
    """

    def __init__(self, change: Callable[[], bool] | None = None) -> None:
        self._change = change or (_raise_windows if sys.platform == "win32" else _nothing)

    def raise_to_normal(self) -> bool:
        """優先度を「通常」に上げる。上げられたら True（上げられなくても通知は続けるので、例外は出さずに False）。"""
        try:
            return self._change()
        except OSError:
            return False
