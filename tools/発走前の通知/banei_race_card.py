"""ばんえいの1レースの通知に載せる中身（見出し・時点・印の順の全頭の表・枠番・騎手・3連単の買い目）。文と画像の両方がここから作られる。
画像は中央・地方と同じ ``RaceImage`` が描く（同じ列の表）。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from 発走前の通知.bet_footer import BetFooter

#: 画像の買い目の欄の札（地方の通知と同じ言葉）。
FOOTER_LABEL = "推奨買目"
#: 1点の金額（円）。
STAKE = 100
#: 買い目の説明（文と画像の買い目の欄に添える）。
NOTES: tuple[str, ...] = (
    "予想の組の確率が 1% 以上で、世間の見立てより 1.5倍以上高い 3連単の組（★ は 2倍以上）",
    "買い目はオッズを見ずに決めている。過去8年の通算は 約120% だが、100% を割る年もある（確かめ中）",
)
#: 買う組が無いときの理由。
NO_PICKS = "世間の見立てよりずれて高い 3連単の組が無い"


@dataclass(frozen=True)
class BaneiRaceCard:
    #: 場と R（例 ``ばんえい帯広 9R``）。
    heading: str
    #: レース名（無ければ空）。
    name: str
    #: 発走時刻（例 ``18:30 発走``。無ければ空）。
    post: str
    #: 時点（``当日の時点`` か、馬体重が届く前の時点）。
    timing: str
    race_day: bool
    #: 印の順（◎○▲△☆注、最後に無印）に並べた全頭。列名は ``今週の予想.forecast_columns``。
    table: pd.DataFrame
    #: 馬番 → 枠番。
    frames: Mapping[int, int]
    #: 馬番 → 騎手名（略称）。
    jockeys: Mapping[int, str] = field(default_factory=dict)
    #: 3連単の買い目の行（1着の馬ごとに1行。例 ``3連単 ★8→1→7・8→1→3``）。
    lines: tuple[str, ...] = ()
    #: 3連単の点数。
    points: int = 0
    #: 馬場水分の1行（例 ``馬場水分 2.4%``）。
    track: str = ""
    #: 馬番 → 推定脚質。ばんえいには脚質が無いので空（表には「-」と出る）。
    styles: Mapping[int, str] = field(default_factory=dict)
    #: 見出しの札（期待度）。ばんえいには期待度が無いので空。
    badge: str = ""

    @property
    def title(self) -> str:
        """例 ``ばんえい帯広 9R テスト特別（18:30 発走）``。"""
        name = f" {self.name}" if self.name else ""
        post = f"（{self.post}）" if self.post else ""
        return f"{self.heading}{name}{post}"

    @property
    def total(self) -> str:
        return f"合計 {self.points}点 {self.points * STAKE:,}円（1点 {STAKE}円）"

    @property
    def footer(self) -> BetFooter:
        """画像の買い目の欄（3連単の行・合計・説明）。買う組が無ければ「なし」と理由。"""
        if not self.lines:
            return BetFooter(FOOTER_LABEL, notes=(NO_PICKS,))
        return BetFooter(FOOTER_LABEL, self.lines, self.total, NOTES)
