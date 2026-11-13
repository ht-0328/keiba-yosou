"""大穴が2頭以上来たレースで、来た大穴の前後の脚質の組み合わせ（前・前、前・後ろ、後ろ・後ろ …）を、結果のペースごとに数える表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent
from .pace_share_table import PACES

_ORDER = {"前": 0, "中": 1, "後ろ": 2}


@dataclass(frozen=True)
class PairPatternTable:
    """``column`` は組み合わせを作る列（既定は結果の前後の脚質 ``front_or_back``。4コーナーの位置 ``corner4_group`` なども渡せる）。"""

    column: str = "front_or_back"

    def build(self, runners: pd.DataFrame, races: pd.DataFrame, title: str) -> Table:
        multi = races.loc[races["longshot_multi"] & races["pace"].isin(PACES)]
        placed = runners.loc[runners["longshot"] & (runners["top3"] > 0) & runners["race_id"].isin(multi.index)]
        pattern = placed.groupby("race_id")[self.column].agg(self._pattern)
        table = pd.DataFrame({"pattern": pattern, "pace": multi["pace"].reindex(pattern.index)})
        counts = pd.crosstab(table["pattern"], table["pace"]).reindex(columns=list(PACES), fill_value=0)
        totals = counts.sum()
        rows = [[str(name), *[f"{int(row[pace])}（{percent(row[pace], totals[pace])}）" for pace in PACES], int(row.sum())]
                for name, row in counts.sort_values(list(PACES), ascending=False).iterrows()]
        rows.append(["（レース数）", *[int(totals[pace]) for pace in PACES], int(totals.sum())])
        return Table(["来た大穴の組み合わせ", *[f"結果が{pace}" for pace in PACES], "計"], rows, title=title,
                     note="（ ）は、そのペースの大穴2頭以上のレースの中の割合。位置の分からない馬は組み合わせから除いた。")

    @staticmethod
    def _pattern(values: pd.Series) -> str:
        known = sorted(values.dropna().tolist(), key=lambda value: (_ORDER.get(value, 9), value))
        return "・".join(known) if known else "（不明）"
