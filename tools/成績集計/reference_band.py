"""数を帯に分けて名前を付ける（基準のページの表の行の値）。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

UNKNOWN = "不明"


@dataclass(frozen=True)
class ReferenceBand:
    """``edges`` の各値を「その値未満」の境目にして ``labels`` を付ける。``labels`` は ``edges`` より1つ多い。

    値が無い行は ``unknown`` の帯に入る（帯の並びでは最後）。表の行の並びが帯の順になるよう、順序付きのカテゴリで返す。
    """

    edges: tuple[float, ...]
    labels: tuple[str, ...]
    unknown: str = UNKNOWN

    def __post_init__(self) -> None:
        if len(self.labels) != len(self.edges) + 1:
            raise ValueError(f"帯の名前は境目より1つ多く要ります: {self.labels}")

    def label(self, values: pd.Series) -> pd.Categorical:
        numbers = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
        # 境目以下の数 = 何番目の帯か（値 < edges[i] なら i 番目）
        index = np.searchsorted(np.asarray(self.edges, dtype=float), numbers, side="right")
        names = np.asarray(self.labels, dtype=object)[np.minimum(index, len(self.labels) - 1)]
        names = np.where(np.isnan(numbers), self.unknown, names)
        return pd.Categorical(names, categories=[*self.labels, self.unknown], ordered=True)
