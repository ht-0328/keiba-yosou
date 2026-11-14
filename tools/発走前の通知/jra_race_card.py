"""中央の1レースの通知に載せる中身（見出し・時点・期待度・馬場の傾向・印の順の全頭の表・枠番・推定脚質・実際に買う買い目）。
文と画像の両方がここから作られる。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from 発走前の通知.bet_footer import BetFooter

#: 画像の買い目の欄の札。
FOOTER_LABEL = "買い目"
#: 重賞の、印で組む買い方の見出し（参考。実際に買う買い目の合計には入らない）。
MARK_BETS_LABEL = "印の買い目（参考・1点 100円）"


@dataclass(frozen=True)
class JraRaceCard:
    #: 場と R（例 ``京都 11R``）。レース一覧に無いレースは予想の見出し。
    heading: str
    #: レース名（無ければ空）。
    name: str
    #: 発走時刻（例 ``15:40 発走``。無ければ空）。
    post: str
    #: 時点（例 ``当日の時点``）。
    timing: str
    race_day: bool
    #: 期待度の1行（``RaceGrades.text()``。例 ``期待度 A（点数 0.21）``）。
    grades: str
    #: 印の順（◎○▲△☆注消、最後に無印）に並べた全頭。列名は ``今週の予想.forecast_columns``。消は危険な人気馬だけ。
    table: pd.DataFrame
    #: 馬番 → 枠番（馬番の色づけに使う。無い馬は色を付けない）。
    frames: Mapping[int, int]
    #: 実際に買う買い目の行（``RaceDescriber.bought`` の書き方）と、その行の金額。
    bets: tuple[tuple[str, int], ...]
    #: 買わないときの理由（買い目があれば空）。
    notes: tuple[str, ...] = ()
    #: その日の馬場の傾向の1行（``TrackTendency.text()``。先に終わった同じ芝ダのレースが無ければ空）。
    tendency: str = ""
    #: 馬番 → 推定脚質（逃げ・先行・差し・追込。``RaceStyles``）。過去走の無い馬は入らない。
    styles: Mapping[int, str] = field(default_factory=dict)
    #: 重賞のときの、印で組む買い方の行（``RaceDescriber.mark_bets``。参考で、1点 100円で数えた額。重賞でなければ空）。
    mark_bets: tuple[str, ...] = ()
    #: 画像の見出しの札（``RaceGrades.badge()``。例 ``期待度 A``。出せなければ空）。地方と同じ形。
    grade_badge: str = ""

    @property
    def badge(self) -> str:
        """画像の見出しの札（例 ``期待度 A``。出せなければ空）。"""
        return self.grade_badge

    @property
    def title(self) -> str:
        """例 ``京都 11R みやこＳ（15:35 発走）``。"""
        name = f" {self.name}" if self.name else ""
        post = f"（{self.post}）" if self.post else ""
        return f"{self.heading}{name}{post}"

    @property
    def yen(self) -> int:
        """このレースで買う金額の合計。"""
        return sum(yen for _, yen in self.bets)

    @property
    def footer(self) -> BetFooter:
        """画像の買い目の欄（券種ごとの行・合計・理由）。"""
        notes = (*self.notes, *(f"{MARK_BETS_LABEL} {line}" for line in self.mark_bets))
        if not self.bets:
            return BetFooter(FOOTER_LABEL, notes=notes)
        return BetFooter(FOOTER_LABEL, tuple(line for line, _ in self.bets), f"合計 {self.yen:,}円", notes)
