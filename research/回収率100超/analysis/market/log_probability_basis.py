"""確率を、条件付きロジットに渡せる説明変数（折れ線の基底）に変える。"""

from __future__ import annotations

import numpy as np

#: 折れ線の節。log の確率の範囲（おおよそ exp(-7)=0.0009 〜 exp(-1)=0.37）を覆う。
DEFAULT_KNOTS: tuple[float, ...] = (-7.0, -6.0, -5.0, -4.0, -3.0, -2.0, -1.5, -1.0)


class LogProbabilityBasis:
    """確率 ``p`` を ``log p`` と、節ごとの折れ線に分ける。

    単純に ``log p`` を1列だけ渡すと、「市場の確率を何乗するか」しか学べない。それでは人気薄が
    買われすぎる歪みの形を表せなかった（べき乗の補正では、100倍超の馬のずれが残った）。
    節ごとに折れ曲がれるようにすると、人気帯ごとに違う補正を学べる。
    """

    def __init__(self, knots: tuple[float, ...] = DEFAULT_KNOTS) -> None:
        self._knots = knots

    @property
    def width(self) -> int:
        """作る列の数。"""
        return 1 + len(self._knots)

    def build(self, probability: np.ndarray) -> np.ndarray:
        """``probability`` から、行数 × ``width`` の説明変数を作る。"""
        x = np.log(np.clip(probability, 1e-9, None))
        return np.column_stack([x] + [np.maximum(x - knot, 0.0) for knot in self._knots])
