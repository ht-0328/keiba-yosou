"""勝ち馬の勝ち方の形（後ろから速い上がりで差した・いつもより前で運んだ・いつもどおり前で運んだ）を、結果のペースごとに数える表。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

from .cells import percent
from .pace_share_table import PACES

#: 勝ち方の形（この順に1つに決める）。
SHAPES: tuple[str, ...] = ("後ろから上がり3位以内で差した", "いつもより前で運んで残った", "いつもどおり前で運んで残った", "そのほか")
_NOTE = ("後ろ = 最初のコーナーで差し・追込の位置（前から3分の1より後ろ）。いつもより前 = 最初のコーナーの位置が、近5走の平均より 0.25 以上前"
         "（頭数で 0〜1 にした位置で）。どれも結果側の値で、何が起きたかを理解するためだけに使う。（ ）はそのペースの勝ち馬の中の割合。")


@dataclass(frozen=True)
class WinShapeTable:
    """``winners``（1着の馬の行。``front_or_back``・``last3f_rank``・``position_shift``・``pace`` が要る）を形 × 結果のペースで数える。"""

    def build(self, winners: pd.DataFrame, title: str) -> Table:
        shape = pd.Series(np.select(
            [(winners["front_or_back"] == "後ろ") & (winners["last3f_rank"] <= 3),
             (winners["front_or_back"] == "前") & (winners["position_shift"] == "いつもより前"),
             winners["front_or_back"] == "前"], list(SHAPES[:3]), default=SHAPES[3]), index=winners.index)
        known = winners["pace"].isin(PACES)
        counts = pd.crosstab(shape[known], winners.loc[known, "pace"]).reindex(index=list(SHAPES), columns=list(PACES), fill_value=0)
        totals = counts.sum()
        rows = [[name, *[f"{int(row[pace])}（{percent(row[pace], totals[pace])}）" for pace in PACES],
                 f"{int(row.sum())}（{percent(row.sum(), totals.sum())}）"] for name, row in counts.iterrows()]
        rows.append(["（勝ち馬の数）", *[int(totals[pace]) for pace in PACES], int(totals.sum())])
        return Table(["勝ち方の形", *[f"結果が{pace}" for pace in PACES], "計"], rows, title=title, note=_NOTE)
