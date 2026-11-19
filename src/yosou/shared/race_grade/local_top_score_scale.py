"""地方の ◎ の点数: ◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1）を S・A・B・C にする（道具「印の成績」の表13 の地方の分け方）。"""

from __future__ import annotations

import math

from .grade_scale import GRADES

#: 人が読む名前と意味（印の成績の表13 で使う）。
TOP_SCORE_LABEL = "◎の点数"
TOP_SCORE_MEANING = "◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1）。高いほど ◎ の単勝・複勝の的中率と回収率が高い"
#: 期待値の重み。中央の ◎ランク（重み 1）を地方に当てると勝率は順に上がるが単勝回収率が上がらず（地方は確率の高い ◎ ほど買われすぎ）、
#: 重みを 2・2.5・3・4・5 と変えると 3 までは勝率も回収率も順に上がり、4 以上で S の勝率が A を下回った（研究「地方の期待度」の docs/01）。
TOP_SCORE_WEIGHT = 3.0
#: 下の線（点数）。S は 0.45 以上、A は 0.15 以上、B は −0.10 以上、C はそれ未満。
#: 2024年の当日の未見の予測の点数の分位（上から 20%・30%・30%・20%）で決めて 0.05 刻みに丸め、2025・2026年で ◎ の単勝・複勝の
#: 勝率・複勝率・回収率が等級の順に上がることを確かめた（線は固定）。
TOP_SCORE_LINES: dict[str, float] = {"S": 0.45, "A": 0.15, "B": -0.10, "C": -math.inf}


class LocalTopScoreScale:
    """地方の ◎ の点数の等級（研究「地方の期待度」の docs/01）。

    点数 = ◎ の1着になる確率 ＋ ``TOP_SCORE_WEIGHT`` ×（◎ の単勝の期待値 − 1）。「当たりやすさ」と「市場より得か」を足したもので、
    等級が高いほど ◎ の単勝・複勝をべた買いしたときの的中率と回収率が高い。期待値が無い（オッズの無い出馬表の時点）なら点数も等級も None。
    通知の期待度は直前の買い目の線への近さ（``LocalExpectationScale``）で、この点数ではない。
    """

    @staticmethod
    def score(win_probability: float | None, win_value: float | None) -> float | None:
        """点数。どちらかが無ければ None。"""
        if win_probability is None or win_value is None or math.isnan(win_probability) or math.isnan(win_value):
            return None
        return float(win_probability + TOP_SCORE_WEIGHT * (win_value - 1.0))

    def of(self, score: float | None) -> str | None:
        if score is None or math.isnan(score):
            return None
        return next(grade for grade in GRADES if score >= TOP_SCORE_LINES[grade])

    def grade(self, win_probability: float | None, win_value: float | None) -> str | None:
        """等級（S・A・B・C）。点数を出せなければ None（見送りは無い）。"""
        return self.of(self.score(win_probability, win_value))

    @staticmethod
    def legend() -> str:
        """人が読む線の説明。"""
        return (f"{TOP_SCORE_LABEL}は ◎ の1着の確率 ＋ {TOP_SCORE_WEIGHT:g} ×（単勝の期待値 − 1）。"
                f"S {TOP_SCORE_LINES['S']:g} 以上・A {TOP_SCORE_LINES['A']:g} 以上・B {TOP_SCORE_LINES['B']:g} 以上・C {TOP_SCORE_LINES['B']:g} 未満")
