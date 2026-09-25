"""人気帯。custom_binary の popularity: {min, max} にそのまま書ける。"""

import numpy as np
import pandas as pd

from yosou.shared.feature.value_types import as_numbers

#: 段ごとの人気帯（両端を含む）。各段は全頭を重なりなく分ける。
LEVELS = {
    "全人気": {"全人気": {}},
    "人気帯": {
        "1〜3番人気": {"min": 1, "max": 3}, "4〜6番人気": {"min": 4, "max": 6},
        "7〜9番人気": {"min": 7, "max": 9}, "10番人気以下": {"min": 10},
    },
}


class PopularityBands:
    """段ごとに、行 → 人気帯の番号（人気が不明なら -1）。"""

    def __init__(self, popularity: pd.Series) -> None:
        self._popularity = as_numbers(popularity).to_numpy()

    def codes(self, level: str) -> np.ndarray:
        codes = np.full(len(self._popularity), -1, dtype=np.int64)
        for code, bounds in enumerate(LEVELS[level].values()):
            low, high = bounds.get("min", 1), bounds.get("max", np.inf)
            codes[(self._popularity >= low) & (self._popularity <= high)] = code
        return codes

    @staticmethod
    def labels(level: str) -> dict[int, tuple[str, dict]]:
        return dict(enumerate(LEVELS[level].items()))
