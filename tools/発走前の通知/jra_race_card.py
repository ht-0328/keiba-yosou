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
#: 全レースの印の買い目の見出し（どの組が当たっても払った額より多く戻る割合で分ける）。
MARK_RETURN_LABEL = "印の買い目"


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
    #: 馬番 → 騎手名（略称。``RaceJockeys``）。無い馬は入らない。
    jockeys: Mapping[int, str] = field(default_factory=dict)
    #: 重賞のときの、印で組む買い方の行（``RaceDescriber.mark_bets``。参考で、1点 100円で数えた額。重賞でなければ空）。
    mark_bets: tuple[str, ...] = ()
    #: 画像の見出しの札（``RaceGrades.badge()``。例 ``期待度 A``。出せなければ空）。地方と同じ形。
    grade_badge: str = ""
    #: 全レースの印の買い目の1行（当たったときの倍率と見込みの回収率）と、買い方ごとの行（``RaceDescriber.mark_returns``。同じ金額の組をまとめた形と金額。当日の予想でなければ空）。
    mark_return: str = ""
    mark_returns: tuple[str, ...] = ()
    #: AI＋ロジック予想の1行（``LogicForecast.line``。印の買い目を AI と同じく買うか、ロジックで見送るか。当日の予想でなければ空）。
    #: AI だけの予想の文と画像には入れず、続けて別の投稿で出す（``RaceMessage.logic_text``）。
    logic: str = ""
    #: 高配当の買い目の投稿の行（``RaceDescriber.high_payout_bets``。1行目は見出し、続けて券種ごとの行。買う点が無ければ「なし（理由）」の1行。当日でない予想と前の版の予想は空）。
    #: AI だけの予想の文と画像には入れず、AI＋ロジック予想のあとに別の投稿で出す（``RaceMessage.high_payout_text``）。
    high_payout: tuple[str, ...] = ()
    #: 的中実績の公開ルールの1行（``PublicRule.line``。◎ の単勝を買うか、「なし（理由）」。当日の予想でなければ空）。AI だけの予想の文の、実際に買う買い目のあとに出す。
    public_rule: str = ""

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
        returns = (f"{MARK_RETURN_LABEL} {self.mark_return}", *(f"{MARK_RETURN_LABEL} {line}" for line in self.mark_returns)) if self.mark_return else ()
        notes = (*self.notes, *returns,
                 *(f"{MARK_BETS_LABEL} {line}" for line in self.mark_bets))
        if not self.bets:
            return BetFooter(FOOTER_LABEL, notes=notes)
        return BetFooter(FOOTER_LABEL, tuple(line for line, _ in self.bets), f"合計 {self.yen:,}円", notes)
