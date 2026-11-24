"""「予想が買っている穴馬」の決まり。"""

from __future__ import annotations

import numpy as np

#: 穴馬とみなす単勝人気の下限（6番人気から）。
LONGSHOT_FIRST_POPULARITY = 6
#: 予想の3着以内の確率が、複勝オッズから見た3着以内率をこれ以上上回る馬を「買っている」とみなす。
LONGSHOT_MIN_EDGE = 0.05


def is_backed_longshot(popularity: np.ndarray, edge: np.ndarray) -> np.ndarray:
    """6番人気以下で、予想が複勝の市場より 0.05 以上高く見ている馬か。例: 8番人気・差 0.07 → 真。欠損値は偽。"""
    return (popularity >= LONGSHOT_FIRST_POPULARITY) & (edge >= LONGSHOT_MIN_EDGE)
