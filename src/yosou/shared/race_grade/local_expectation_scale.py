"""地方の期待度: そのレースの推奨買目の期待の儲け（Σ（期待値 − 1））を S・A・B・C にする。"""

from __future__ import annotations

import math
from collections.abc import Iterable

from .grade_scale import GRADES

#: 人が読む名前と意味（通知の文・表の画像で使う）。
EXPECTATION_LABEL = "期待度"
EXPECTATION_MEANING = "推奨買目の期待の儲け（1点ごとの 期待値 − 1 の合計）。高いほど、そのレースの推奨買目の1日の儲けと的中率が高い"
#: 期待度の下の線（点数）。S は 3.2 以上、A は 1.4 以上、B は 0.5 以上、C はそれ未満。
#: 過去のレースの推奨買目を本番と同じ決まりで作り直し、2024年の点数の分位（上から 20%・30%・30%・20%）で決めて 0.1 刻みに丸めた。
#: 2025・2026年で、等級の順に推奨買目の1日の儲けと的中率が上がり、S の回収率がいちばん高いことを確かめた（研究「地方の期待度」の docs/02）。
EXPECTATION_LINES: dict[str, float] = {"S": 3.2, "A": 1.4, "B": 0.5, "C": -math.inf}


class LocalExpectationScale:
    """地方のレースに添える1つの目安「期待度」（設計書「買うレースと買い目を決める」の 11）。

    点数 = そのレースの推奨買目の1点ごとの（期待値 − 1）の合計。1点 100円で買ったときに見込める儲けを 100円単位で数えたもので、
    買い目の割の良さと点数の多さの両方が入る。推奨買目が1点も無ければ点数も等級も None。
    """

    @staticmethod
    def score(values: Iterable[float]) -> float | None:
        """点数。期待値が1つも無ければ None。"""
        numbers = [float(value) for value in values if value is not None and not math.isnan(float(value))]
        if not numbers:
            return None
        return float(sum(value - 1.0 for value in numbers))

    def of(self, score: float | None) -> str | None:
        if score is None or math.isnan(score):
            return None
        return next(grade for grade in GRADES if score >= EXPECTATION_LINES[grade])

    def grade(self, values: Iterable[float]) -> str | None:
        """期待度（S・A・B・C）。推奨買目が無ければ None。"""
        return self.of(self.score(values))

    @staticmethod
    def legend() -> str:
        """人が読む線の説明。"""
        return (f"{EXPECTATION_LABEL}の点数は推奨買目の（期待値 − 1）の合計。"
                f"S {EXPECTATION_LINES['S']:g} 以上・A {EXPECTATION_LINES['A']:g} 以上・B {EXPECTATION_LINES['B']:g} 以上・C {EXPECTATION_LINES['B']:g} 未満")
