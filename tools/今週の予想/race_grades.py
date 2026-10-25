"""レースの目安（◎ランク・的中率・配当率と、その等級）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yosou.shared.race_grade import GradeScale, TopRankScale

#: 予想の結果（JSON）の鍵。レースに1組（全頭に共通）。
RANK_SCORE, RANK = "rank_score", "rank"
HIT_RATE = "hit_rate"
PAYOUT_RATE, PAYOUT_GRADE = "payout_rate", "payout_grade"
GRADE_KEYS: tuple[str, ...] = (RANK_SCORE, RANK, HIT_RATE, PAYOUT_RATE, PAYOUT_GRADE)
#: 人が読む名前と意味（表の注・画面・全頭の予想根拠で使う）。
RANK_LABEL, HIT_LABEL, PAYOUT_LABEL = "◎ランク", "的中率", "配当率"
RANK_MEANING = "◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数。高いほど ◎ の単勝・複勝の的中率と回収率が高い"
HIT_MEANING = "◎ の単勝が当たる確率（1着になる確率）"
PAYOUT_MEANING = "配当が中荒れ以上になる確率（荒れ具合の予想の単勝・馬連・3連複・3連単の平均）"


@dataclass(frozen=True)
class RaceGrades:
    """1レースの ◎ランク（点数と S・A・B・C）・的中率（◎ の1着の確率）・配当率（0〜1）とその等級（S・A・B・C）。出せなかったものは None
    （設計書「買うレースと買い目を決める」の 03 の 5）。

    ◎ランクの点数は ◎ の1着の確率 ＋（◎ の単勝の期待値 − 1）で、線は ``TopRankScale``（S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満）。
    配当率は荒れ具合の予想の4券種の「中荒れ以上の確率」の平均で、線は ``GradeScale``（S 75% 以上・A 50% 以上・B 25% 以上・C 25% 未満）。
    """

    rank_score: float | None
    rank: str | None
    hit_rate: float | None
    payout_rate: float | None
    payout_grade: str | None

    def as_dict(self) -> dict[str, Any]:
        """予想の結果（JSON）に入れる形。"""
        return {RANK_SCORE: self.rank_score, RANK: self.rank, HIT_RATE: self.hit_rate, PAYOUT_RATE: self.payout_rate, PAYOUT_GRADE: self.payout_grade}

    @classmethod
    def from_dict(cls, forecast: dict[str, Any]) -> RaceGrades:
        """予想の結果（JSON）から戻す。鍵の無い前の版の結果は、全部 None。"""
        return cls(forecast.get(RANK_SCORE), forecast.get(RANK), forecast.get(HIT_RATE), forecast.get(PAYOUT_RATE), forecast.get(PAYOUT_GRADE))

    def text(self) -> str:
        """一覧や表の注に出す1行。例: ``◎ランク A（的中率 23%）・配当率 S（82%）``。出せなかったものは ``なし``。"""
        rank = "なし" if self.rank is None else f"{self.rank}（{HIT_LABEL} {_percent(self.hit_rate)}）"
        return f"{RANK_LABEL} {rank}・{PAYOUT_LABEL} {_grade_text(self.payout_grade, self.payout_rate)}"

    def text_if_any(self) -> str:
        """``text()`` と同じだが、◎ランクも配当率も無い（目安を出す前の版の結果）なら空。レースの一覧や状況の要約に使う。"""
        return self.text() if self.rank is not None or self.payout_grade is not None else ""

    def lines(self) -> list[str]:
        """全頭の予想根拠の頭に書く3行（意味つき）。"""
        score = "なし" if self.rank is None or self.rank_score is None else f"{self.rank}（点数 {self.rank_score:.2f}）"
        return [f"- {RANK_LABEL}: {score}。{RANK_MEANING}",
                f"- {HIT_LABEL}: {_percent(self.hit_rate)}。{HIT_MEANING}",
                f"- {PAYOUT_LABEL}: {_grade_text(self.payout_grade, self.payout_rate)}。{PAYOUT_MEANING}"]

    @staticmethod
    def legend() -> str:
        """意味と線の説明（表の注・画面の凡例）。"""
        return (f"{RANK_LABEL}は{RANK_MEANING}（{TopRankScale.legend()}）。{HIT_LABEL}は{HIT_MEANING}。"
                f"{PAYOUT_LABEL}は{PAYOUT_MEANING}で、等級は {GradeScale.legend()}")


def _percent(rate: float | None) -> str:
    return "なし" if rate is None else f"{rate:.0%}"


def _grade_text(grade: str | None, rate: float | None) -> str:
    return "なし" if grade is None or rate is None else f"{grade}（{rate:.0%}）"
