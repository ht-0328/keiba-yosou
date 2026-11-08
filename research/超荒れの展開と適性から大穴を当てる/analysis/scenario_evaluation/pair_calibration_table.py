"""中穴・大穴2頭以上の確率の帯ごとの実際の割合と、いちばん確率の高い組がそろって来た割合を、作り方ごと・期間ごとに並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..tables.cells import percent
from .evaluation_frame import CONFIRM, EXPLORE

_BANDS = ([-0.01, 0.05, 0.10, 0.15, 0.20, 0.30, 1.0], ["〜5%", "5〜10%", "10〜15%", "15〜20%", "20〜30%", "30%〜"])
_NOTE = ("2頭以上 = 4番人気以下の馬が3着以内に2頭以上。確率は、展開の型ごとに全頭の3着以内の確率の合計を 3 にそろえ、その中では各馬が独立に来るとみなして出し、"
         "予想のペースの確率で混ぜたもの。「展開の型で混ぜない」は、混ぜた確率をそのまま使ったもの、「市場」はオッズから見た3着以内率を使ったもの。"
         "組の的中 = いちばん確率の高い4番人気以下の2頭が、そろって3着以内に来たレースの割合。上位5組 = 確率の高い順の5組のどれかがそろって来た割合。")


@dataclass(frozen=True)
class PairCalibrationTable:
    """``results`` は（作り方の名前 → （``PairProbability.races`` のレースの表, 組の表））。"""

    def build(self, results: dict[str, tuple[pd.DataFrame, pd.DataFrame]], title: str) -> Table:
        rows = []
        for name, (races, pairs) in results.items():
            for period in (EXPLORE, CONFIRM):
                part = races.loc[races["period"] == period]
                ids = set(part["race_id"])
                top5 = pairs.loc[pairs["race_id"].isin(ids) & (pairs["rank"] <= 5)].groupby("race_id")["hit"].any()
                multi = part["actual"] >= 2
                rows.append([name, period, "全レース", len(part), f"{part['two_or_more'].mean() * 100:.1f}%", percent(multi.sum(), len(part)),
                             percent(part["pair_hit"].sum(), len(part)), percent(top5.sum(), len(part))])
                bands = pd.cut(part["two_or_more"], _BANDS[0], labels=_BANDS[1])
                for label, group in part.groupby(bands, observed=True):
                    rows.append([name, period, str(label), len(group), f"{group['two_or_more'].mean() * 100:.1f}%",
                                 percent((group["actual"] >= 2).sum(), len(group)), percent(group["pair_hit"].sum(), len(group)),
                                 percent(top5.reindex(group["race_id"]).fillna(False).sum(), len(group))])
        columns = ["作り方", "期間", "2頭以上の確率の帯", "レース数", "確率の平均", "実際に2頭以上", "組の的中", "上位5組のどれかの的中"]
        return Table(columns, rows, title=title, note=_NOTE)
