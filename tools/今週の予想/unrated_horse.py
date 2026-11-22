"""評価できない馬（海外・地方の成績が DB に無い招待馬）を見分ける。"""

from __future__ import annotations

import pandas as pd

#: 所属が招待（地方招待・外国招待。JV-Data の東西所属コード 3・4。``共通.codes.AFFILIATION_NAMES``）の値。
INVITED = "招待"
#: 印の理由に書く文。
REASON = ("所属が招待で、中央の過去走が DB に無い（海外・地方の成績が DB に無い）。オッズが無く、過去の同じ種類の招待馬の成績でも評価できないので、"
          "印を付けない")


class UnratedHorse:
    """所属が招待で、この DB に中央の過去走が1つも無い馬を「評価できない馬」とする。

    DB は中央の成績しか持たないので、こうした馬は近走・相手関係・能力などの材料が空になり、モデルの確率はほぼ市場の評価（オッズ）だけで決まる。
    ほかの人気馬をモデルが割り引くと、データが無いだけのこの馬の単勝の期待値が相対的に1位になって ◎ が付いてしまう（G1 に来た外国馬で起きた）。
    中央で走ったことのある招待馬と、初出走の中央の馬（新馬戦など。所属は美浦・栗東）は、この決まりに入らない。
    """

    def of(self, affiliation: pd.Series, runs_before: pd.Series) -> pd.Series:
        """``affiliation`` は所属（美浦・栗東・招待）、``runs_before`` は今回より前の中央の出走数（無ければ欠損値）。戻り値は真偽の列。"""
        runs = pd.to_numeric(runs_before, errors="coerce").fillna(0)
        return (affiliation.astype(str) == INVITED) & (runs <= 0)
