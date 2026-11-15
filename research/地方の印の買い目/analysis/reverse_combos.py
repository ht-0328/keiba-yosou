"""馬単の印の組（◎→○▲☆）から、裏の組（○▲☆→◎）を作る。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 裏の買い方の名前（中央の印の買い目と同じ）。
REVERSE_RULE = "馬単（裏）"
_EXACTA = "馬単"


@dataclass(frozen=True)
class ReverseCombos:
    """``of(marks)`` は、印の組の表（``MarkCombos`` の列）の馬単の行の 1着と2着を入れ替えた行（買い方 ``REVERSE_RULE``）。
    オッズと払戻は入れ替えた組のものが要るので欠損値にし、外した印（``dropped``）は付けない。"""

    def of(self, marks: pd.DataFrame) -> pd.DataFrame:
        exacta = marks[marks["rule"] == _EXACTA]
        return exacta.assign(rule=REVERSE_RULE, a=exacta["b"].to_numpy(), b=exacta["a"].to_numpy(),
                             odds=float("nan"), payout=float("nan"), dropped=False).reset_index(drop=True)
