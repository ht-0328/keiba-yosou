"""0〜1 の確率を S・A・B・C の4つの等級にする。"""

from __future__ import annotations

import math

#: 等級の並び（良い順）。
GRADES: tuple[str, ...] = ("S", "A", "B", "C")
#: 等級の下の線（0〜1）。S は 0.75 以上、A は 0.50 以上、B は 0.25 以上、C はそれ未満（利用者の決定。100点で S = 100〜75・A = 75〜50・B = 50〜25・C = 25〜0）。
LOWER_LINES: dict[str, float] = {"S": 0.75, "A": 0.50, "B": 0.25, "C": 0.0}


class GradeScale:
    """確率（0〜1）を等級にする。レースの的中率（◎ の単勝が当たる確率（1着になる確率））と配当率（配当が中荒れ以上になる確率）に同じ線で使う
    （設計書「買うレースと買い目を決める」の 03 の 5）。

    線は下の線を含む（0.75 は S、0.50 は A、0.25 は B）。確率が無い（None・NaN）なら None。
    """

    def of(self, probability: float | None) -> str | None:
        if probability is None or math.isnan(probability):
            return None
        return next(grade for grade in GRADES if probability >= LOWER_LINES[grade])

    @staticmethod
    def legend() -> str:
        """人が読む線の説明。例: ``S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満``。"""
        parts = [f"{grade} {LOWER_LINES[grade]:.0%} 以上" for grade in GRADES[:-1]]
        return "・".join([*parts, f"{GRADES[-1]} {LOWER_LINES[GRADES[-2]]:.0%} 未満"])
