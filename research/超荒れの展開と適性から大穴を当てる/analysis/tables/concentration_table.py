"""大穴が来たレースの中で、どの大穴が来たかを切り口ごとに数え、市場の見立てと比べる表（集まり方）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import ratio

_NOTES = {
    "won": ("大穴が1着のレースの大穴だけを数える。「市場から見た数」は、各レースの大穴のオッズから見た勝率を、そのレースの大穴の中で合計 1 にそろえて足したもの"
            "（「大穴のどれかが勝った」と分かったうえで、市場の見立てどおりなら勝つはずの数）。集まり方 = 来た数 ÷ 市場から見た数。1 より大きければ、"
            "大穴が勝つときにその切り口の大穴が市場の見立てより多く勝っている。"),
    "top3": ("大穴が3着以内に2頭以上のレースの大穴だけを数える。「市場から見た数」は、各馬の人気から見た3着以内率を、そのレースの大穴の中で"
             "「3着以内に来た大穴の頭数」にそろえて足したもの。集まり方 = 来た数 ÷ 市場から見た数。"),
}


@dataclass(frozen=True)
class ConcentrationTable:
    """``longshots`` は対象のレースの大穴の行。``target`` は ``won``（1着）か ``top3``（3着以内）。"""

    target: str = "won"

    def build(self, longshots: pd.DataFrame, cuts: list[str], title: str, min_runs: int = 20) -> Table:
        frame = longshots.assign(expected=self._expected(longshots))
        rows = []
        for values, part in frame.groupby(cuts, observed=True, sort=True):
            if len(part) < min_runs:
                continue
            labels = list(values) if isinstance(values, tuple) else [values]
            hits, expected = float(part[self.target].sum()), float(part["expected"].sum())
            rows.append([*[str(label) for label in labels], len(part), int(hits), f"{expected:.1f}", ratio(hits, expected)])
        return Table([*cuts, "大穴の頭数", "来た数", "市場から見た数", "集まり方"], rows, title=title, note=_NOTES[self.target])

    def _expected(self, longshots: pd.DataFrame) -> pd.Series:
        race = longshots["race_id"]
        if self.target == "won":
            implied = 1.0 / longshots["win_odds"].where(longshots["win_odds"] > 0)
            return implied / implied.groupby(race).transform("sum")
        share = longshots["expected_top3"] / longshots["expected_top3"].groupby(race).transform("sum")
        return share * longshots["top3"].groupby(race).transform("sum")
