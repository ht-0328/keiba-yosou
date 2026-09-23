"""ウォークフォワードの期間の区切り。"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class YearSplit:
    """1回ぶんの区切り。``fit`` で学習し、``valid`` で木の本数を決め、``test`` で評価する。"""

    test_year: int
    fit: np.ndarray
    valid: np.ndarray
    test: np.ndarray


class WalkForwardYears:
    """「その年より前で学習して、その年を予測する」を年ごとにくり返す。

    1回だけ期間を3つに分けると、その半年の当たり外れの偶然がそのまま結論になってしまう。
    年ごとにくり返すと、同じ作り方が年をまたいで通じるかが分かる。
    直前の1年は、木の本数を決める（早期終了の）ためだけに使い、学習には使わない。
    """

    def __init__(self, year: np.ndarray, first_test_year: int, last_test_year: int) -> None:
        self._year = year
        self._first_test_year = first_test_year
        self._last_test_year = last_test_year

    def __iter__(self) -> Iterator[YearSplit]:
        for test_year in range(self._first_test_year, self._last_test_year + 1):
            test = self._year == test_year
            if not test.any():
                continue
            valid = self._year == test_year - 1
            yield YearSplit(test_year, (self._year < test_year) & ~valid, valid, test)
