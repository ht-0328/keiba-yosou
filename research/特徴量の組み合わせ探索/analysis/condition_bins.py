"""馬の条件の候補（1つの特徴量の値の範囲）。見つける期間の値の分布から作り、後ろの期間にも同じ範囲を当てる。"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.feature.feature_kind import FeatureKind
from yosou.shared.feature.value_types import as_numbers

#: 数値の特徴量を分ける数（5つなら下位20%ずつ）。
QUANTILES = 5
#: カテゴリの特徴量で候補にする値の数（見つける期間の出走数の多い順）と、最低の出走数。
TOP_VALUES = 30
MIN_VALUE_RUNS = 500


@dataclass(frozen=True)
class ConditionBins:
    """``codes`` は行ごとの条件の番号（当てはまらなければ -1）、``labels`` は 番号 → (名前, conditions の値)。"""

    name: str
    codes: np.ndarray
    labels: dict[int, tuple[str, object]]

    @classmethod
    def fit(cls, name: str, column: pd.Series, kind: FeatureKind, discover: np.ndarray) -> "ConditionBins":
        if kind is FeatureKind.CATEGORICAL:
            return cls._categorical(name, column.astype(str), discover)
        return cls._numeric(name, as_numbers(column), discover)

    @classmethod
    def _categorical(cls, name: str, values: pd.Series, discover: np.ndarray) -> "ConditionBins":
        counts = values[discover].value_counts()
        counts = counts[(counts >= MIN_VALUE_RUNS) & (counts.index != "nan")].head(TOP_VALUES)
        chosen = list(counts.index)
        codes = values.map({value: code for code, value in enumerate(chosen)}).fillna(-1).to_numpy(dtype=np.int64)
        return cls(name, codes, {code: (f"{name}が{value}", [value]) for code, value in enumerate(chosen)})

    @classmethod
    def _numeric(cls, name: str, values: pd.Series, discover: np.ndarray) -> "ConditionBins":
        known = values[discover].dropna()
        if known.nunique() < 2:
            return cls(name, np.full(len(values), -1, dtype=np.int64), {})
        edges = np.unique(np.quantile(known, np.linspace(0, 1, QUANTILES + 1)))
        # 各範囲は [下の端, 次の下の端)。最後の範囲だけ上の端を含み、上限を付けない。最初の範囲は下限を付けない。
        codes = np.searchsorted(edges[1:-1], values.to_numpy(), side="right").astype(np.int64)
        codes[values.isna().to_numpy()] = -1
        labels = {}
        for code in range(len(edges) - 1):
            low = None if code == 0 else float(edges[code])
            high_values = known[known < edges[code + 1]] if code < len(edges) - 2 else None
            high = None if high_values is None else float(high_values.max())
            labels[code] = (range_label(name, low, high), {k: v for k, v in (("min", low), ("max", high)) if v is not None})
        return cls(name, codes, labels)


def range_label(name: str, low: float | None, high: float | None) -> str:
    low_text = "" if low is None else f"{low:g}以上"
    high_text = "" if high is None else f"{high:g}以下"
    return f"{name}が{low_text}{high_text}"
