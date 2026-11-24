"""地方の期待度: 直前の買い目の線への近さを S・A・B・C にする。"""

from __future__ import annotations

import math

from .grade_scale import GRADES

#: 人が読む名前と意味（通知の文・表の画像で使う）。
EXPECTATION_LABEL = "期待度"
EXPECTATION_MEANING = "直前の買い目の線への近さ（買い目を決める時刻に分かることだけで出す）。線にいちばん近い馬の単勝の回収率は S がいちばん高く、C がいちばん低い"
#: 期待度の下の線（点数）。S は 1 以上（直前の買い目の買う馬がいるレース）、A は 0.85 以上、B は 0.5 以上、C はそれ未満。
#: 買い目を決める時刻のオッズで時間の順を守って確かめると、線にいちばん近い馬の単勝の回収率は S がどの年もいちばん高く、全体では C がいちばん低い
#: （年によっては B が C と同じくらい低い。道具「地方の直前の買い目」の check.py の2つめの表）。
EXPECTATION_LINES: dict[str, float] = {"S": 1.0, "A": 0.85, "B": 0.5, "C": -math.inf}


class LocalExpectationScale:
    """地方のレースに添える1つの目安「期待度」（設計書「買うレースと買い目を決める」の 11）。

    点数 = 直前の買い目の線への近さ（道具「地方の直前の買い目」の ``LateRule.closeness``。馬ごとに、買う馬らしさ ÷ その線 と 戻りの見込み ÷ その線 の
    小さいほうを取り、レースでいちばん大きい値）。1 以上なら、そのレースに直前の買い目の買う馬がいる。点数が無ければ等級も None。
    """

    def of(self, score: float | None) -> str | None:
        if score is None or math.isnan(score):
            return None
        return next(grade for grade in GRADES if score >= EXPECTATION_LINES[grade])

    @staticmethod
    def legend() -> str:
        """人が読む線の説明。"""
        return (f"{EXPECTATION_LABEL}の点数は直前の買い目の線への近さ。"
                f"S {EXPECTATION_LINES['S']:g} 以上・A {EXPECTATION_LINES['A']:g} 以上・B {EXPECTATION_LINES['B']:g} 以上・C {EXPECTATION_LINES['B']:g} 未満")
