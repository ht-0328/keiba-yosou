"""大穴が2頭以上来たレースで、来た大穴どうしが同じ形（前後の脚質・4コーナーの位置・枠の側・いつもとの位置の差）だったかの表。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import pandas as pd

from 共通.render import Table

from .cells import percent

#: 見る形（表の見出し → 列）。
ATTRIBUTES: dict[str, str] = {
    "前後の脚質（結果）": "front_or_back",
    "4コーナーの位置（前・中・後ろ）": "corner4_group",
    "枠の側（内・中・外）": "horse_side",
    "いつもとの位置の差": "position_shift",
}
_NOTE = ("来た大穴の組 = 同じレースで3着以内に来た大穴の2頭ずつの組。比べる基準は「同じレースの大穴から、でたらめに2頭選んだ組」"
         "（そのレースの大穴の形の混ざり方なら、たまたまこれだけ同じになる）と、「全レースの1〜3着の2頭ずつの組」（ふつうの決着）。")


@dataclass(frozen=True)
class PairAlignmentTable:
    """``runners``（全部の出走）と、大穴2頭以上のレースの race_id の並び ``multi_races`` から作る。"""

    def build(self, runners: pd.DataFrame, multi_races: pd.Index, title: str) -> Table:
        longshots = runners.loc[runners["longshot"] & runners["race_id"].isin(multi_races)]
        placed = longshots.loc[longshots["top3"] > 0]
        podium = runners.loc[runners["top3"] > 0]
        rows = []
        for label, column in ATTRIBUTES.items():
            hit, hit_n = self._same_share(placed, column)
            base, base_n = self._same_share(longshots, column)
            usual, usual_n = self._same_share(podium, column)
            rows.append([label, hit_n, percent(hit, hit_n), percent(base, base_n), percent(usual, usual_n)])
        columns = ["形", "来た大穴の組の数", "来た大穴の組で同じ形", "同じレースの大穴をでたらめに組んだとき", "全レースの1〜3着の組"]
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _same_share(runs: pd.DataFrame, column: str) -> tuple[int, int]:
        """同じレースの2頭ずつの組のうち、``column`` の値が同じ組の数と、組の数（値の欠けた馬は除く）。"""
        same = total = 0
        for values in runs.dropna(subset=[column]).groupby("race_id")[column]:
            for first, second in combinations(values[1].tolist(), 2):
                total += 1
                same += int(first == second)
        return same, total
