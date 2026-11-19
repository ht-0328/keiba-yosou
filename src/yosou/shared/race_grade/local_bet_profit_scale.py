"""地方の推奨買目の期待の儲け（Σ（期待値 − 1））を S・A・B・C にする（研究「地方の期待度」が、確定オッズで作り直した推奨買目を分けるのに使う）。"""

from __future__ import annotations

import math
from collections.abc import Iterable

from .grade_scale import GRADES

#: 人が読む名前と意味（研究の表で使う）。
BET_PROFIT_LABEL = "推奨買目の期待の儲け"
BET_PROFIT_MEANING = "推奨買目の1点ごとの 期待値 − 1 の合計。確定オッズで作り直した推奨買目では、高いほど1日の儲けと的中率が高い"
#: 下の線（点数）。S は 3.2 以上、A は 1.4 以上、B は 0.5 以上、C はそれ未満。
#: 過去のレースの推奨買目を確定オッズで作り直し、2024年の点数の分位（上から 20%・30%・30%・20%）で決めて 0.1 刻みに丸めた（研究「地方の期待度」の docs/02）。
BET_PROFIT_LINES: dict[str, float] = {"S": 3.2, "A": 1.4, "B": 0.5, "C": -math.inf}


class LocalBetProfitScale:
    """地方の推奨買目の期待の儲けの等級（研究「地方の期待度」の docs/02）。

    点数 = そのレースの推奨買目の1点ごとの（期待値 − 1）の合計。1点 100円で買ったときに見込める儲けを 100円単位で数えたもの。
    確定オッズで作り直した推奨買目では等級の順に成績が並ぶが、通知の時刻のオッズでは見込みが膨らんで並ばない（研究の docs/03）ので、
    通知の期待度（``LocalExpectationScale``）には使わない。推奨買目が1点も無ければ点数も等級も None。
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
        return next(grade for grade in GRADES if score >= BET_PROFIT_LINES[grade])

    def grade(self, values: Iterable[float]) -> str | None:
        """期待度（S・A・B・C）。推奨買目が無ければ None。"""
        return self.of(self.score(values))

    @staticmethod
    def legend() -> str:
        """人が読む線の説明。"""
        return (f"{BET_PROFIT_LABEL}は推奨買目の（期待値 − 1）の合計。"
                f"S {BET_PROFIT_LINES['S']:g} 以上・A {BET_PROFIT_LINES['A']:g} 以上・B {BET_PROFIT_LINES['B']:g} 以上・C {BET_PROFIT_LINES['B']:g} 未満")
