"""◎ の点数（1着の確率 ＋ 単勝の期待値 − 1）を S・A・B・C の ◎ランクにする。"""

from __future__ import annotations

import math

from .grade_scale import GRADES

#: ◎ランクの下の線（点数）。S は 0.35 以上、A は 0.15 以上、B は 0 以上、C はそれ未満。
#: 2015〜2018年の当日の予想で決め、2019〜2026年で ◎ の単勝・複勝のべた買いの的中率と回収率がランクの順に上がることを確かめた
#: （研究「全レース全券種の買い方」の docs/02。線は固定）。
RANK_LINES: dict[str, float] = {"S": 0.35, "A": 0.15, "B": 0.0, "C": -math.inf}


class TopRankScale:
    """◎ の点数を ◎ランク（S・A・B・C）にする（設計書「買うレースと買い目を決める」の 03 の 5）。

    点数 = ◎ の1着になる確率 ＋（◎ の単勝の期待値 − 1）。「当たりやすさ」と「市場より得か」を足したもので、ランクが高いほど
    ◎ の単勝・複勝をべた買いしたときの的中率と回収率が高い。期待値が無い（木曜。オッズが無い）なら点数もランクも None。
    """

    @staticmethod
    def score(win_probability: float | None, win_value: float | None) -> float | None:
        """点数。どちらかが無ければ None。"""
        if win_probability is None or win_value is None or math.isnan(win_probability) or math.isnan(win_value):
            return None
        return float(win_probability + (win_value - 1.0))

    def of(self, score: float | None) -> str | None:
        if score is None or math.isnan(score):
            return None
        return next(grade for grade in GRADES if score >= RANK_LINES[grade])

    @staticmethod
    def legend() -> str:
        """人が読む線の説明。"""
        return "◎ランクの点数は ◎ の1着の確率 ＋ 単勝の期待値 − 1。S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満"
