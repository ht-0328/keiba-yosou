"""切り口ごとに、大穴が1着・3着以内に2頭以上・1〜3着が全部大穴 のレースの数と割合を並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent
from .race_cuts import CUTS

_NOTE = ("大穴 = 確定の単勝人気が10番人気以下。「市場が見た大穴1着」は、大穴のオッズから見た勝率の合計をレースについて足したもの"
         "（市場の見立てどおりなら、この数だけ大穴が勝つ）。最後の行は比べる基準（表の対象の全レース）。")


@dataclass(frozen=True)
class UpsetCountTable:
    """``races``（``RaceTable`` の表）を ``cut`` で分ける。``by_count`` なら大穴1着の多い順に ``limit`` 行まで並べる。"""

    def build(self, races: pd.DataFrame, cut: str, title: str, by_count: bool = False, limit: int | None = None) -> Table:
        grouped = races.assign(cut=CUTS[cut](races)).groupby("cut", observed=True)
        summary = grouped.agg(races=("longshot_won", "size"), won=("longshot_won", "sum"), multi=("longshot_multi", "sum"),
                              all3=("longshot_all", "sum"), market=("longshot_market", "sum"))
        if by_count:
            summary = summary.sort_values(["won", "multi", "races"], ascending=False)
        if limit is not None:
            summary = summary.head(limit)
        rows = [self._row(str(value), row) for value, row in summary.iterrows()]
        total = pd.Series({"races": len(races), "won": races["longshot_won"].sum(), "multi": races["longshot_multi"].sum(),
                           "all3": races["longshot_all"].sum(), "market": races["longshot_market"].sum()})
        rows.append(self._row("（全レース）", total))
        columns = [cut, "レース数", "大穴1着", "割合", "市場が見た大穴1着", "大穴2頭以上", "割合", "3頭とも大穴", "割合"]
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _row(label: str, row: pd.Series) -> list[object]:
        return [label, int(row["races"]), int(row["won"]), percent(row["won"], row["races"]), f"{row['market']:.1f}",
                int(row["multi"]), percent(row["multi"], row["races"]), int(row["all3"]), percent(row["all3"], row["races"], 2)]
