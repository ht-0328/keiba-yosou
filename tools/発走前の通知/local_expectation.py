"""地方の1レースの期待度（直前の買い目の線への近さの点数と S・A・B・C）。通知の文の見出しの下の1行と、表の画像の見出しの札に出す。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.race_grade import EXPECTATION_LABEL, LocalExpectationScale

from 地方の直前の買い目.late_bets import LateBets

#: 出せないときの字と、理由。
NONE = "なし"
NO_LATE_REASON = "見込みを出せない"
NOT_RACE_DAY_REASON = "馬体重が届く前の前日の時点では出さない。当日の時点で出す"


@dataclass(frozen=True)
class LocalExpectation:
    """1レースの期待度（設計書「買うレースと買い目を決める」の 11）。点数は直前の買い目（道具「地方の直前の買い目」）の線への近さ
    （``LateBets.closeness``。買い目を決める時刻に分かることだけで出す値で、1 以上なら直前の買い目の買う馬がいる）。当日の時点だけ出す。
    直前の買い目のファイルが無い・2つのモデルの値を出せなかったレースは、点数も等級も None で ``reason`` に理由。買い目はこの値で変えない。"""

    score: float | None
    grade: str | None
    reason: str = ""

    @classmethod
    def of(cls, late: LateBets | None) -> LocalExpectation:
        """発走前の予想が書いた直前の買い目から出す。"""
        if late is None or late.closeness is None:
            reason = f"{NO_LATE_REASON}: {late.reason}" if late is not None and late.reason else NO_LATE_REASON
            return cls(None, None, reason)
        return cls(late.closeness, LocalExpectationScale().of(late.closeness))

    @classmethod
    def not_race_day(cls) -> LocalExpectation:
        """前日の時点（当日の時点で出す）。"""
        return cls(None, None, NOT_RACE_DAY_REASON)

    def text(self) -> str:
        """通知の文の1行。例 ``期待度 A（点数 0.91）``。出せなければ ``期待度 なし（理由）``。"""
        if self.grade is None or self.score is None:
            return f"{EXPECTATION_LABEL} {NONE}（{self.reason or NO_LATE_REASON}）"
        return f"{EXPECTATION_LABEL} {self.grade}（点数 {self.score:.2f}）"

    def badge(self) -> str:
        """表の画像の見出しの札。例 ``期待度 A``。出せなければ空（札を描かない）。"""
        return f"{EXPECTATION_LABEL} {self.grade}" if self.grade is not None else ""
