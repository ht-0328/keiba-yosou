"""地方の1レースの通知に載せる中身（見出し・時点・期待度・馬場の傾向・印の順の全頭の表・枠番・推定脚質・買い目）。文と画像の両方がここから作られる。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from 地方の直前の買い目.late_bets import LateBets

from 地方の推奨買目.mark_bets import MarkBets

from 高知ファイナルの買い目.final_bets import FinalBets

from 発走前の通知.bet_footer import BetFooter
from 発走前の通知.local_expectation import LocalExpectation

#: 画像の買い目の欄の札（印の買い目。中央の通知と同じ言葉）。
MARK_LABEL = "印の買い目"


@dataclass(frozen=True)
class LocalRaceCard:
    #: 場と R（例 ``園田 5R``）。レース一覧に無いレースは predict の見出し。
    heading: str
    #: レース名（無ければ空）。
    name: str
    #: 発走時刻（例 ``12:40 発走``。無ければ空）。
    post: str
    #: 時点（``当日の時点`` か ``前日の時点（馬体重が届く前なのでオッズだけ）``）。
    timing: str
    race_day: bool
    #: 印の順（◎○▲△☆注、最後に無印）に並べた全頭。列名は ``今週の予想.forecast_columns``。
    table: pd.DataFrame
    #: 馬番 → 枠番（馬番の色づけに使う。無い馬は色を付けない）。
    frames: Mapping[int, int]
    #: その日の馬場の傾向の1行（``TrackTendency.text()``。先に終わった同じ芝ダのレースが無ければ空）。
    tendency: str = ""
    #: 馬番 → 推定脚質（逃げ・先行・差し・追込。``RaceStyles.local()``）。過去走の無い馬は入らない。
    styles: Mapping[int, str] = field(default_factory=dict)
    #: 馬番 → 騎手名（略称。``RaceJockeys``）。無い馬は入らない。
    jockeys: Mapping[int, str] = field(default_factory=dict)
    #: レースの期待度（直前の買い目の線への近さの点数と S・A・B・C。``LocalExpectation.of``）。買い目はこれで変えない。
    expectation: LocalExpectation = field(default_factory=lambda: LocalExpectation(None, None))
    #: 印の買い目（``MarkRecommender``。当日の時点だけ。無ければ空）。
    marks: MarkBets = field(default_factory=MarkBets)
    #: 直前の買い目（道具「地方の直前の買い目」。当日の時点だけ。ファイルが無ければ None で、文に出さない）。確かめ中。
    late: LateBets | None = None
    #: 高知ファイナルの買い目（道具「高知ファイナルの買い目」。高知のその日の最終レース「ファイナルレース」だけ。ファイルが無ければ None で、文に出さない）。
    kochi_final: FinalBets | None = None

    @property
    def badge(self) -> str:
        """画像の見出しの札（例 ``期待度 A``。出せなければ空）。"""
        return self.expectation.badge()

    @property
    def title(self) -> str:
        """例 ``園田 5R ＨＵＫ企画☆超短距離スーパースプリント（12:40 発走）``。"""
        name = f" {self.name}" if self.name else ""
        post = f"（{self.post}）" if self.post else ""
        return f"{self.heading}{name}{post}"

    @property
    def footer(self) -> BetFooter:
        """画像の買い目の欄（印の買い目の見出し（買うか見送りか・合計・戻る額）と、買い方ごとの行）。
        買い方の行が無い（前日の時点・出せなかった）ときは「なし」と、あれば理由。"""
        if self.marks.empty:
            return BetFooter(MARK_LABEL, notes=() if self.race_day else ("馬体重が届く前の前日の時点では出さない",))
        if not self.marks.lines:
            return BetFooter(MARK_LABEL, notes=(self.marks.heading,))
        return BetFooter(MARK_LABEL, (self.marks.heading, *self.marks.lines))
