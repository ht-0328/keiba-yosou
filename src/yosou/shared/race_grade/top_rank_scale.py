"""中央の期待度: ◎ の単勝の期待値が線未満なら「見送り」、線以上なら ◎ の1着の確率 ＋ 1.25 ×（単勝の期待値 − 1）の点数を S・A・B・C にする。"""

from __future__ import annotations

import math

from .grade_scale import GRADES

#: 期待値の重み。重み 0〜10 と等級の割合を変えて比べ、見送りの線と合わせて、2023〜2024年でも 2025〜2026年でも
#: どの等級も ◎ の単勝回収率が 100% を超え、勝率が S → C の順に下がったもの（研究「中央の期待度」の docs/01）。
RANK_VALUE_WEIGHT = 1.25
#: 見送りの線（◎ の単勝の期待値）。これ未満のレースは、◎ の単勝回収率がどちらの期間でも 100% を割ったので等級を付けない。
SKIP_VALUE = 0.90
#: 見送りのレースの等級の字。
SKIP_GRADE = "見送り"
#: 期待度の下の線（点数）。S は 0.28 以上、A は 0.14 以上、B は 0.02 以上、C はそれ未満。
#: 2023〜2024年の当日の未見の予測の、見送りでないレースの点数の分位（上から 20%・30%・30%・20%）を小数2桁に丸めた（線は固定）。
RANK_LINES: dict[str, float] = {"S": 0.28, "A": 0.14, "B": 0.02, "C": -math.inf}


class TopRankScale:
    """中央の期待度（設計書「買うレースと買い目を決める」の 03 の 5）。

    ``grade(1着の確率, 単勝の期待値)`` は、期待値が ``SKIP_VALUE`` 未満なら ``SKIP_GRADE``、それ以外は点数（``score``）を ``of`` で S・A・B・C にする。
    S・A・B・C のどれも ◎ の単勝をべた買いしたときの回収率が 100% を超え、等級が高いほど的中率（勝率）が高い。
    等級の間の回収率の差は、偶然のぶれ（1年で ±10% ほど）より小さく、順に並ぶとは言えない。期待値が無い（木曜。オッズが無い）なら None。
    """

    @staticmethod
    def score(win_probability: float | None, win_value: float | None) -> float | None:
        """点数。どちらかが無ければ None。"""
        if win_probability is None or win_value is None or math.isnan(win_probability) or math.isnan(win_value):
            return None
        return float(win_probability + RANK_VALUE_WEIGHT * (win_value - 1.0))

    def of(self, score: float | None) -> str | None:
        """点数を S・A・B・C にする（見送りの判定はしない。``grade`` を使う）。"""
        if score is None or math.isnan(score):
            return None
        return next(grade for grade in GRADES if score >= RANK_LINES[grade])

    def grade(self, win_probability: float | None, win_value: float | None) -> str | None:
        """期待度（S・A・B・C か ``SKIP_GRADE``）。期待値か確率が無ければ None。"""
        score = self.score(win_probability, win_value)
        if score is None:
            return None
        return SKIP_GRADE if win_value < SKIP_VALUE else self.of(score)

    @staticmethod
    def legend() -> str:
        """人が読む線の説明。"""
        return (f"◎ の単勝の期待値が {SKIP_VALUE:.2f} 未満なら{SKIP_GRADE}。それ以外は 1着の確率 ＋ {RANK_VALUE_WEIGHT:g} ×（単勝の期待値 − 1）の点数で "
                f"S {RANK_LINES['S']:g} 以上・A {RANK_LINES['A']:g} 以上・B {RANK_LINES['B']:g} 以上・C {RANK_LINES['B']:g} 未満")
