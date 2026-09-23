"""採用した買い方（どの券種を、どの期待値から買うか）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BetRule:
    """期待値が ``lower`` 以上の買い目を、1点 ``stake`` 円で買う。

    線を 1 ちょうどにしないのは、確率にも払戻倍率の見積もりにも誤差があるためで、
    その誤差のぶんだけ余裕を取る。

    **線の値は、前半の期間（2019〜2021年）の回収率だけを見て決めた。**
    後半（2022〜2026年）の結果を見てから動かすと、線の選び方そのものが過剰適合になる。
    前半では、線を上げるほど回収率が上がり、1.30 で頭打ちになった。線を上げるほど買い目は減る。
    1.20 は、前半で 100% を超え、かつ年 300点以上の買い目が残る値として選んだ。
    """

    lower: float
    stake: float = 100.0

    def selects(self, expected_value: pd.Series) -> pd.Series:
        """買うかどうか（真偽の列）。期待値が欠けている行は買わない。"""
        return expected_value.notna() & (expected_value >= self.lower)

    def describe(self) -> str:
        return f"期待値 {self.lower:.2f} 以上・1点 {self.stake:.0f}円"


#: 採用する買い方。複勝を、期待値 1.20 以上のときだけ買う。
PLACE_RULE = BetRule(lower=1.20)
