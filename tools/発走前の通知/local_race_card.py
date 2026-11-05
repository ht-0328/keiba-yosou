"""地方の1レースの通知に載せる中身（見出し・時点・印の順の全頭の表・枠番・買い目）。文と画像の両方がここから作られる。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from 発走前の通知.local_bets import LocalBets


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
    bets: LocalBets

    @property
    def title(self) -> str:
        """例 ``園田 5R ＨＵＫ企画☆超短距離スーパースプリント（12:40 発走）``。"""
        name = f" {self.name}" if self.name else ""
        post = f"（{self.post}）" if self.post else ""
        return f"{self.heading}{name}{post}"
