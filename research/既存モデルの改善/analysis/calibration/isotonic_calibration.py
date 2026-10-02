"""isotonic regression で確率をそろえ直す。"""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression

#: 較正後の確率の端（0 と 1 ちょうどにしない）。
_EDGE = 1e-4


class IsotonicCalibration:
    """isotonic regression（確率の順を保ったまま、帯ごとの実際の割合に合う階段の形に直す）で確率をそろえ直す。

    形を決めないので、Platt scaling では直せない曲がったずれも直せる。そのかわり、データの少ない端（高い確率）では
    階段が偶然で大きく振れやすい。
    """

    def __init__(self) -> None:
        self._regression: IsotonicRegression | None = None

    def fit(self, probability: np.ndarray, label: np.ndarray) -> IsotonicCalibration:
        regression = IsotonicRegression(out_of_bounds="clip", y_min=_EDGE, y_max=1.0 - _EDGE)
        self._regression = regression.fit(np.asarray(probability, dtype="float64"), label)
        return self

    def apply(self, probability: np.ndarray) -> np.ndarray:
        if self._regression is None:
            raise RuntimeError("まだ学んでいません（fit を先に呼んでください）")
        return self._regression.predict(np.asarray(probability, dtype="float64"))
