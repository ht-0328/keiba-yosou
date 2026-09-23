"""危険な人気馬を候補から外す。"""

from __future__ import annotations

import pandas as pd

from ..column_names import DANGER_PROB

#: 危険とみなす「4着以下になる確率」の線。人気馬モデルの学習の報告が「危険」と呼んでいる線と同じ。
DANGEROUS_THRESHOLD = 0.6


class DangerousFavoriteFilter:
    """危険確率（人気馬モデルの「4着以下になる確率」）がしきい値以上の馬を、買い目の候補から外す。

    人気馬でない馬（危険確率が欠損）は外さない。ルール集の WID-03・SRF-02・SRT-04 に当たる。
    """

    def __init__(self, threshold: float = DANGEROUS_THRESHOLD) -> None:
        self._threshold = threshold

    @property
    def threshold(self) -> float:
        return self._threshold

    def apply(self, runners: pd.DataFrame) -> pd.DataFrame:
        is_dangerous = runners[DANGER_PROB] >= self._threshold
        return runners[~is_dangerous.fillna(False)]
