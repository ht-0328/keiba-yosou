"""地方の1レースの通知に載せる中身（見出し・時点・馬場の傾向・印の順の全頭の表・枠番・推定脚質・買い目）。文と画像の両方がここから作られる。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from 地方の推奨買目.recommendation import STAKE
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知.bet_footer import BetFooter

#: 画像の買い目の欄の札。
FOOTER_LABEL = "推奨買目"


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
    #: 実際に買う買い目（推奨買目＋全頭の予想の単勝・複勝）。無ければ理由を持つ。
    bets: RecommendationSet
    #: その日の馬場の傾向の1行（``TrackTendency.text()``。先に終わった同じ芝ダのレースが無ければ空）。
    tendency: str = ""
    #: 馬番 → 推定脚質（逃げ・先行・差し・追込。``RaceStyles.local()``）。過去走の無い馬は入らない。
    styles: Mapping[int, str] = field(default_factory=dict)

    @property
    def title(self) -> str:
        """例 ``園田 5R ＨＵＫ企画☆超短距離スーパースプリント（12:40 発走）``。"""
        name = f" {self.name}" if self.name else ""
        post = f"（{self.post}）" if self.post else ""
        return f"{self.heading}{name}{post}"

    @property
    def footer(self) -> BetFooter:
        """画像の買い目の欄（推奨買目の券種ごとの行・合計・理由）。"""
        notes = tuple(part for part in self.bets.reason.split("。") if part)
        if self.bets.none:
            return BetFooter(FOOTER_LABEL, notes=notes)
        total = f"合計 {self.bets.points}点 {self.bets.yen:,}円（1点 {STAKE}円）"
        return BetFooter(FOOTER_LABEL, tuple(self.bets.lines()), total, notes)
