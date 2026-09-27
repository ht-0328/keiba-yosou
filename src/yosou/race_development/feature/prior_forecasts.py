"""後の組に渡す、前の組の予測（傾向・前半・後半）の束。"""

from __future__ import annotations

from dataclasses import dataclass

from .group_forecast import GroupForecast


@dataclass(frozen=True)
class PriorForecasts:
    """後の組の特徴量（V・S・T）の元になる、前の組の予測（設計書 01 の「流れ」）。

    - ``tendency``: 傾向の組（既存の予想）の予測。前半・後半・着順のすべての予想に入れる（V）。
    - ``early``: 前半の組の予測。後半と着順の予想に入れる（S）。
    - ``late``: 後半の組の予測。着順の予想に入れる（T）。

    まだ予測していない組は None。どれも、そのサンプルを学習に使っていないモデルの予測である（設計書 11 の決まり 11）。
    """

    tendency: GroupForecast | None = None
    early: GroupForecast | None = None
    late: GroupForecast | None = None

    def with_early(self, early: GroupForecast) -> PriorForecasts:
        """前半の組の予測を足したもの。"""
        return PriorForecasts(self.tendency, early, self.late)

    def with_late(self, late: GroupForecast) -> PriorForecasts:
        """後半の組の予測を足したもの。"""
        return PriorForecasts(self.tendency, self.early, late)
