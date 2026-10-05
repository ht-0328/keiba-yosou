"""1レースの、レース前の材料が DB にどこまで入っているか。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

#: 結果の入ったデータ区分（3 速報成績（3着まで）〜 7 成績（確定））。
_RESULT_STAGES: tuple[str, ...] = ("3", "4", "5", "6", "7")
#: レース中止のデータ区分。
_CANCELLED_STAGE = "9"
#: 木曜の出走馬名表（枠番・馬番が未定）と、金・土の出馬表のデータ区分。
_NAME_LIST_STAGE, _CARD_STAGE = "1", "2"
#: 発表月日時分（``MMDDHHMM``）の桁数。
_ANNOUNCED_LENGTH = 8


@dataclass(frozen=True)
class RaceSignals:
    """1レースの見出しと、出馬表・馬体重・馬場状態・締め切り前のオッズの有無。値は表に出す形にしてある。

    ``odds_announced_at`` は締め切り前の単勝オッズのいちばん新しい断面の発表月日時分（``MMDDHHMM``。無ければ None）、
    ``odds_count`` はその断面でオッズの付いている馬の数。``entries`` は出走馬の数（取消を含む）、``numbered`` は馬番の決まった馬の数、
    ``weighed`` は馬体重の出ている馬の数。``going`` は馬場状態（良 / 稍重 / 重 / 不良 / 未発表）。
    """

    rid: str
    race_date: str
    venue_code: str
    venue: str
    race_no: int
    post_time: str | None
    race_name: str
    class_name: str
    course: str
    stage: str
    stage_name: str
    entries: int
    numbered: int
    weighed: int
    going: str
    going_announced: bool
    odds_announced_at: str | None
    odds_count: int

    @property
    def has_odds(self) -> bool:
        """締め切り前の単勝オッズが1頭でも入っているか。"""
        return self.odds_count > 0

    @property
    def is_numbered(self) -> bool:
        """出馬表（全頭の馬番が決まっている）か。木曜の出走馬名表の間は偽。"""
        return self.entries > 0 and self.numbered == self.entries

    @property
    def is_weighed(self) -> bool:
        """馬体重が発表されたと見るか（半分以上の馬に出ている）。"""
        return self.entries > 0 and self.weighed * 2 >= self.entries

    @property
    def is_name_list(self) -> bool:
        """木曜の出走馬名表（枠番・馬番が未定）の段階か。"""
        return self.stage == _NAME_LIST_STAGE

    @property
    def is_card(self) -> bool:
        """金・土の出馬表（枠番・馬番が決まった）の段階か。結果が入ると偽。"""
        return self.stage == _CARD_STAGE

    @property
    def is_finished(self) -> bool:
        """結果（速報成績か確定成績）が入っているか。"""
        return self.stage in _RESULT_STAGES

    @property
    def is_cancelled(self) -> bool:
        """レース中止か。"""
        return self.stage == _CANCELLED_STAGE

    def odds_announced_datetime(self) -> datetime | None:
        """オッズの発表時刻を日時にする（年は開催日の年）。無ければ None。"""
        text = self.odds_announced_at
        if not text or len(text) != _ANNOUNCED_LENGTH or not text.isdigit():
            return None
        try:
            return datetime(int(self.race_date[:4]), int(text[:2]), int(text[2:4]), int(text[4:6]), int(text[6:8]))
        except ValueError:
            return None

    def post_datetime(self) -> datetime | None:
        """発走の日時。発走時刻が無ければ None。"""
        if not self.post_time:
            return None
        return datetime.fromisoformat(f"{self.race_date}T{self.post_time}:00")
