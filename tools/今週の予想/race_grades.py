"""レースの目安。人に見せるのは期待度（◎ の点数と S・A・B・C）の1つだけ。的中率・配当率は買い方の判断と記録のために持ち続ける。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from yosou.shared.race_grade import EXPECTATION_LABEL, TopRankScale

#: 予想の結果（JSON）の鍵。レースに1組（全頭に共通）。
RANK_SCORE, RANK = "rank_score", "rank"
HIT_RATE = "hit_rate"
PAYOUT_RATE, PAYOUT_GRADE = "payout_rate", "payout_grade"
#: 3連複の荒れ具合（``TrioUpsetJudge`` が決めたもの。6番人気以下を軸にした3連複で買うレースを選ぶのに使う）。
TRIO_UPSET = "trio_upset"
GRADE_KEYS: tuple[str, ...] = (RANK_SCORE, RANK, HIT_RATE, PAYOUT_RATE, PAYOUT_GRADE, TRIO_UPSET)
#: 人が読む名前と意味（通知の文・まとめ・表の注・画面・全頭の予想根拠・印の成績の表13 で使う）。地方の通知と同じ「期待度」の1つにする。
RANK_LABEL = EXPECTATION_LABEL
RANK_MEANING = "◎ の1着の確率 ＋ 単勝の期待値 − 1 の点数。高いほど ◎ の単勝・複勝の的中率と回収率が高い"
#: 期待度を出せないとき（木曜。単勝オッズがまだ無い）の字と理由。
NONE = "なし"
NO_VALUE_REASON = "単勝オッズが出る前なので出さない"


@dataclass(frozen=True)
class RaceGrades:
    """1レースの期待度（◎ の点数 ``rank_score`` と S・A・B・C の ``rank``）・的中率（◎ の1着の確率）・配当率（0〜1）とその等級（S・A・B・C）と、
    3連複の荒れ具合（固い・中荒れ・大荒れ・超荒れ）。出せなかったものは None（設計書「買うレースと買い目を決める」の 03 の 5）。

    人に見せる文（``text``・``lines``・``legend``・``badge``）は、地方の通知と同じく期待度の1つだけにする。点数は ◎ の1着の確率 ＋（◎ の単勝の期待値 − 1）で、
    線は ``TopRankScale``（S 0.35 以上・A 0.15 以上・B 0 以上・C 0 未満）。的中率・配当率・3連複の荒れ具合は文に出さないが、予想の結果（JSON）には
    今までどおり入れる（配当率と3連複の荒れ具合は買い目の判断に使う）。鍵の名前（``rank``・``rank_score``）は前の版の結果と同じ。
    """

    rank_score: float | None
    rank: str | None
    hit_rate: float | None
    payout_rate: float | None
    payout_grade: str | None
    trio_upset: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """予想の結果（JSON）に入れる形。"""
        return {RANK_SCORE: self.rank_score, RANK: self.rank, HIT_RATE: self.hit_rate, PAYOUT_RATE: self.payout_rate, PAYOUT_GRADE: self.payout_grade,
                TRIO_UPSET: self.trio_upset}

    @classmethod
    def from_dict(cls, forecast: dict[str, Any]) -> RaceGrades:
        """予想の結果（JSON）から戻す。鍵の無い前の版の結果は、全部 None。"""
        return cls(forecast.get(RANK_SCORE), forecast.get(RANK), forecast.get(HIT_RATE), forecast.get(PAYOUT_RATE), forecast.get(PAYOUT_GRADE),
                   forecast.get(TRIO_UPSET))

    @property
    def has_grade(self) -> bool:
        """期待度を出せたか（木曜と、目安を出す前の版の結果は出せない）。"""
        return self.rank is not None and self.rank_score is not None

    def text(self) -> str:
        """通知の文・一覧・表の注に出す1行。例: ``期待度 A（点数 0.21）``。出せなければ ``期待度 なし（単勝オッズが出る前なので出さない）``。"""
        if not self.has_grade:
            return f"{RANK_LABEL} {NONE}（{NO_VALUE_REASON}）"
        return f"{RANK_LABEL} {self.rank}（点数 {self.rank_score:.2f}）"

    def text_if_any(self) -> str:
        """``text()`` と同じだが、期待度を出せなければ空。レースの一覧や状況の要約に使う。"""
        return self.text() if self.has_grade else ""

    def badge(self) -> str:
        """表の画像の見出しの札。例 ``期待度 A``。出せなければ空（札を描かない）。"""
        return f"{RANK_LABEL} {self.rank}" if self.has_grade else ""

    def lines(self) -> list[str]:
        """全頭の予想根拠の頭に書く1行（意味つき）。"""
        return [f"- {self.text()}。{RANK_MEANING}"]

    @staticmethod
    def legend() -> str:
        """意味と線の説明（表の注・画面の凡例）。"""
        return f"{RANK_LABEL}は{RANK_MEANING}（{TopRankScale.legend()}）"
