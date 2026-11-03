"""3連複の荒れ具合の4つの確率から、荒れ具合で形を決める3連複のレースの荒れ具合を決める。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import UpsetLevel

#: 超荒れにする、超荒れの確率の線。超荒れはどのレースでも確率がいちばん高いクラスにならないので、確率の線で選ぶ
#: （研究「危険な人気馬を見極める」。この線より上のレースは、3連複が超荒れになる割合が全レースの2倍以上だった）。
HUGE_LINE = 0.18
#: 固いにする、固いの確率の線。固いがいちばん高くてもこの線に届かなければ、固いと言い切れないので中荒れとして扱う
#: （固いのレースでは3連複を買わないので、固いと言い切れないレースは中荒れの形で買う。線はどちらの期間でも全体の回収率を上げた値）。
SOLID_LINE = 0.50


class TrioUpsetJudge:
    """超荒れの確率が ``HUGE_LINE`` 以上なら超荒れ。そうでなければ確率がいちばん高いクラスだが、固いは固いの確率が ``SOLID_LINE`` 以上のときだけで、
    届かなければ中荒れ。"""

    def of(self, probabilities: pd.DataFrame) -> pd.Series:
        """``probabilities`` は1行 = 1レースで、列に固い・中荒れ・大荒れ・超荒れの確率を持つ。行の並びと index はそのまま。"""
        levels = list(UpsetLevel.labels())
        solid, mid, huge = UpsetLevel.SOLID.label, UpsetLevel.MID.label, UpsetLevel.HUGE.label
        shares = probabilities[levels].astype(float)
        top = shares.idxmax(axis=1)
        top = top.where(~((top == solid) & (shares[solid] < SOLID_LINE)), mid)
        return top.where(shares[huge] < HUGE_LINE, huge)
