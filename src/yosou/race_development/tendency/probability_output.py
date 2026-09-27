"""二値の予想の確率を、そのまま1つの列にする。"""

from __future__ import annotations

import numpy as np


class ProbabilityOutput:
    """``TendencyOutput`` を守る。3着以内・4着以下のような二値の予想の確率を、1つの列にする。"""

    def __init__(self, column: str) -> None:
        self._column = column

    @property
    def columns(self) -> tuple[str, ...]:
        return (self._column,)

    def of(self, probabilities: np.ndarray) -> dict[str, np.ndarray]:
        return {self._column: np.asarray(probabilities, dtype="float64").reshape(-1)}
