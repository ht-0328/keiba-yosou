"""決着の分け方ごとに、結果のペース（ハイ・平均・スロー）の割合を並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..theory.race_table import MULTI, OTHER, WIN_ONLY
from .cells import percent

PACES: tuple[str, ...] = ("スロー", "平均", "ハイ")
_NOTE = ("結果のペース = レースの前3ハロンを、開催日の前日までの3年の同じ競馬場・コース・距離・クラスの平均と比べ、"
         "標準偏差の 0.5倍より速ければハイ、遅ければスロー（回顧の表2。展開の予想と同じ区分）。ペースの分からないレースは除く。")


@dataclass(frozen=True)
class PaceShareTable:
    """``races``（``RaceTable``）を決着の分け方で分け、結果のペースの割合を出す。"""

    def build(self, races: pd.DataFrame, title: str) -> Table:
        known = races.loc[races["pace"].isin(PACES)]
        rows = []
        for outcome in (MULTI, WIN_ONLY, OTHER):
            part = known.loc[known["outcome"] == outcome]
            rows.append([outcome, len(part), *[percent((part["pace"] == pace).sum(), len(part)) for pace in PACES]])
        rows.append(["（全レース）", len(known), *[percent((known["pace"] == pace).sum(), len(known)) for pace in PACES]])
        return Table(["決着", "レース数", *PACES], rows, title=title, note=_NOTE)
