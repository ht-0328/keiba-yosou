"""荒れ具合の4段階の確率を、「固い」と「大荒れ以上」の2つの列にする。"""

from __future__ import annotations

import numpy as np

from ..feature import big_upset_probability, calm_probability

#: 荒れ具合のクラスの番号（既存の予想「荒れ具合」の ``UpsetLevel``: 0 固い・1 中荒れ・2 大荒れ・3 超荒れ）。
_CALM = 0
_BIG_AND_ABOVE = (2, 3)


class UpsetOutput:
    """``TendencyOutput`` を守る。1つの券種の荒れ具合の確率（固い・中荒れ・大荒れ・超荒れ）から、2つの列を作る。

    4つの確率は合計が 1 なので、全部を入れると1つは余分になる。展開の材料として分かりやすい両端
    （固く収まりそうか、大きく荒れそうか）だけを残す。
    """

    def __init__(self, bet_key: str) -> None:
        self._calm = calm_probability(bet_key)
        self._big = big_upset_probability(bet_key)

    @property
    def columns(self) -> tuple[str, ...]:
        return (self._calm, self._big)

    def of(self, probabilities: np.ndarray) -> dict[str, np.ndarray]:
        matrix = np.asarray(probabilities, dtype="float64")
        return {self._calm: matrix[:, _CALM], self._big: matrix[:, list(_BIG_AND_ABOVE)].sum(axis=1)}
