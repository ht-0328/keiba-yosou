"""レースの目安（的中率・配当率と、その等級）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yosou.shared.race_grade import GradeScale

#: 予想の結果（JSON）の鍵。レースに1組（全頭に共通）。
HIT_RATE, HIT_GRADE = "hit_rate", "hit_grade"
PAYOUT_RATE, PAYOUT_GRADE = "payout_rate", "payout_grade"
GRADE_KEYS: tuple[str, ...] = (HIT_RATE, HIT_GRADE, PAYOUT_RATE, PAYOUT_GRADE)
#: 人が読む名前と意味（表の注・画面・全頭の予想根拠で使う）。
HIT_LABEL, PAYOUT_LABEL = "的中率", "配当率"
HIT_MEANING = "◎ が3着以内に来る確率"
PAYOUT_MEANING = "配当が中荒れ以上になる確率（荒れ具合の予想の単勝・馬連・3連複・3連単の平均）"


@dataclass(frozen=True)
class RaceGrades:
    """1レースの的中率と配当率（0〜1）と、その等級（S・A・B・C）。出せなかったものは None（設計書「買うレースと買い目を決める」の 03 の 5）。

    的中率は ◎ が3着以内に来る確率（3着以内のモデル）、配当率は配当が中荒れ以上になる確率（荒れ具合の予想の4券種の「中荒れ以上の確率」の平均）。
    等級はどちらも ``GradeScale`` の同じ線（S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満）。
    """

    hit_rate: float | None
    hit_grade: str | None
    payout_rate: float | None
    payout_grade: str | None

    def as_dict(self) -> dict[str, Any]:
        """予想の結果（JSON）に入れる形。"""
        return {HIT_RATE: self.hit_rate, HIT_GRADE: self.hit_grade, PAYOUT_RATE: self.payout_rate, PAYOUT_GRADE: self.payout_grade}

    @classmethod
    def from_dict(cls, forecast: dict[str, Any]) -> RaceGrades:
        """予想の結果（JSON）から戻す。鍵の無い前の版の結果は、全部 None。"""
        return cls(forecast.get(HIT_RATE), forecast.get(HIT_GRADE), forecast.get(PAYOUT_RATE), forecast.get(PAYOUT_GRADE))

    def text(self) -> str:
        """一覧や表の注に出す1行。例: ``的中率 B（38%）・配当率 A（56%）``。出せなかったものは ``なし``。"""
        return f"{HIT_LABEL} {_grade_text(self.hit_grade, self.hit_rate)}・{PAYOUT_LABEL} {_grade_text(self.payout_grade, self.payout_rate)}"

    def text_if_any(self) -> str:
        """``text()`` と同じだが、的中率も配当率も無い（目安を出す前の版の結果）なら空。レースの一覧や状況の要約に使う。"""
        return self.text() if self.hit_grade is not None or self.payout_grade is not None else ""

    def lines(self) -> list[str]:
        """全頭の予想根拠の頭に書く2行（意味つき）。"""
        return [f"- {HIT_LABEL}: {_grade_text(self.hit_grade, self.hit_rate)}。{HIT_MEANING}",
                f"- {PAYOUT_LABEL}: {_grade_text(self.payout_grade, self.payout_rate)}。{PAYOUT_MEANING}"]

    @staticmethod
    def legend() -> str:
        """意味と線の説明（表の注・画面の凡例）。"""
        return f"{HIT_LABEL}は{HIT_MEANING}、{PAYOUT_LABEL}は{PAYOUT_MEANING}。等級は {GradeScale.legend()}"


def _grade_text(grade: str | None, rate: float | None) -> str:
    return "なし" if grade is None or rate is None else f"{grade}（{rate:.0%}）"
