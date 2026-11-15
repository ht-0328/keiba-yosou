"""地方の1レースの期待度（推奨買目の期待の儲けの点数と S・A・B・C）。通知の文の見出しの下の1行と、表の画像の見出しの札に出す。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.race_grade import EXPECTATION_LABEL, LocalExpectationScale

from 地方の推奨買目.recommendation_set import RecommendationSet

#: 出せないときの字と、理由。
NONE = "なし"
NO_BETS_REASON = "推奨買目が無い"
NOT_RACE_DAY_REASON = "馬体重が届く前の前日の時点では出さない。当日の時点で出す"


@dataclass(frozen=True)
class LocalExpectation:
    """1レースの期待度（設計書「買うレースと買い目を決める」の 11）。点数は推奨買目（道具「地方の推奨買目」の8券種）の1点ごとの（期待値 − 1）の合計
    （``LocalExpectationScale``）。当日の時点だけ出す（推奨買目が当日の時点だけなので）。
    推奨買目が1点も無ければ、点数も等級も None で ``reason`` に理由。買い目はこの値で変えない。"""

    score: float | None
    grade: str | None
    reason: str = ""

    @classmethod
    def of(cls, recommended: RecommendationSet) -> LocalExpectation:
        """道具「地方の推奨買目」の推奨買目（全頭の予想の ◎ の単勝・複勝を足す前のもの）から出す。"""
        score = LocalExpectationScale.score(row.value for row in recommended.rows)
        if score is None:
            reason = f"{NO_BETS_REASON}: {recommended.reason}" if recommended.reason else NO_BETS_REASON
            return cls(None, None, reason)
        return cls(score, LocalExpectationScale().of(score))

    @classmethod
    def not_race_day(cls) -> LocalExpectation:
        """前日の時点（当日の時点で出す）。"""
        return cls(None, None, NOT_RACE_DAY_REASON)

    def text(self) -> str:
        """通知の文の1行。例 ``期待度 A（点数 2.10）``。出せなければ ``期待度 なし（理由）``。"""
        if self.grade is None or self.score is None:
            return f"{EXPECTATION_LABEL} {NONE}（{self.reason or NO_BETS_REASON}）"
        return f"{EXPECTATION_LABEL} {self.grade}（点数 {self.score:.2f}）"

    def badge(self) -> str:
        """表の画像の見出しの札。例 ``期待度 A``。出せなければ空（札を描かない）。"""
        return f"{EXPECTATION_LABEL} {self.grade}" if self.grade is not None else ""
