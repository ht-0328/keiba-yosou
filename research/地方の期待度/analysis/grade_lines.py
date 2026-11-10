"""期待度の等級（S・A・B・C）の下の線を、線を決める年の点数の分位から決め、点数を等級にする。"""

from __future__ import annotations

import math
from collections.abc import Mapping

import pandas as pd

from yosou.shared.race_grade import GRADES

#: 等級ごとのレースの割合（上から S・A・B。残りが C）。
DEFAULT_SHARES: tuple[float, float, float] = (0.20, 0.30, 0.30)
#: 線を丸める桁。
_DIGITS = 2


class GradeLines:
    """``decide(scores)`` は、線を決める年の ◎ の点数の並びから、S が上位 ``shares[0]``・A が次の ``shares[1]``・B が次の ``shares[2]``・
    C が残りになる下の線（小数2桁に丸める）を返す。``grade(scores, lines)`` は点数を等級にする（線は下の値を含む。欠損は None）。"""

    def __init__(self, shares: tuple[float, float, float] = DEFAULT_SHARES) -> None:
        if not all(0 < share < 1 for share in shares) or sum(shares) >= 1:
            raise ValueError(f"割合は 0 より大きく、合計が 1 未満にしてください: {shares}")
        self._shares = shares

    def decide(self, scores: pd.Series) -> dict[str, float]:
        values = scores.dropna().astype(float)
        if values.empty:
            raise ValueError("線を決める点数がありません")
        s, a, b = self._shares
        quantiles = values.quantile([1 - s, 1 - s - a, 1 - s - a - b])
        return {"S": round(float(quantiles.iloc[0]), _DIGITS), "A": round(float(quantiles.iloc[1]), _DIGITS),
                "B": round(float(quantiles.iloc[2]), _DIGITS), "C": -math.inf}

    @staticmethod
    def grade(scores: pd.Series, lines: Mapping[str, float]) -> pd.Series:
        def of(score: float) -> str | None:
            if score is None or math.isnan(score):
                return None
            return next(grade for grade in GRADES if score >= lines[grade])

        return scores.astype(float).map(of)

    @staticmethod
    def legend(lines: Mapping[str, float]) -> str:
        """例 ``S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満``。"""
        parts = [f"{grade} {lines[grade]:g} 以上" for grade in GRADES[:-1]]
        return "・".join([*parts, f"{GRADES[-1]} {lines[GRADES[-2]]:g} 未満"])
