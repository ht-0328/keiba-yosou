"""パターンが使う探索の軸。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PatternNeeds:
    """参加パターンが、探索の格子のどの軸を使うか。使わない軸は格子で回さない（無駄な組み合わせを作らない）。

    - ``upset``: 荒れ度のしきい値。``form``・``danger``: 本命の確率・危険確率のしきい値。``top_k``: 週の上位 k。
    - ``wide``・``narrow``: 広め・少点数の買い方。
    """

    upset: bool = False
    form: bool = False
    danger: bool = False
    top_k: bool = False
    wide: bool = False
    narrow: bool = False

    def __or__(self, other: PatternNeeds) -> PatternNeeds:
        return PatternNeeds(
            self.upset or other.upset, self.form or other.form, self.danger or other.danger,
            self.top_k or other.top_k, self.wide or other.wide, self.narrow or other.narrow,
        )
