"""このプロセスを P コアに絞る。"""

from __future__ import annotations

import sys

#: P コア（論理 CPU 0〜11）のマスク。LightGBM と CatBoost が E コアに載ると止まったように遅くなることがある。
P_CORES_MASK = 0xFFF


class PCoreAffinity:
    """Windows では、このプロセス（と、そこから作られる学習のスレッド）を P コアだけで動かす。ほかの OS では何もしない。

    同じマシンでほかの学習が動いていることがあるので、学習は並べずに1つずつ走らせ、コアも絞る
    （研究「一番人気を疑う」の ``port_check.py`` と同じ決まり）。
    """

    def __init__(self, mask: int = P_CORES_MASK) -> None:
        self._mask = mask

    def apply(self) -> bool:
        """絞ったら True。Windows 以外は何もせず False。"""
        if sys.platform != "win32":
            return False
        import ctypes

        kernel = ctypes.windll.kernel32
        kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), self._mask)
        return True
