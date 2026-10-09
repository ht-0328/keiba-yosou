"""基準のページの節に置く、距離の変更（短縮・同じ・延長）ごとの成績の表。成績7つに「人気から見た差」の2列を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.popularity_expectation import PopularityExpectation, PopularityGap

from 成績集計.reference_table_spec import EMPTY
from 成績集計.reference_tally import PERF_HEADER, ReferenceTally

#: 成績7つのあとに足す列。
GAP_HEADER: tuple[str, ...] = ("人気から見た勝率の差", "人気から見た複勝率の差")


@dataclass(frozen=True)
class DistanceChangeTableSpec:
    """``column``（距離の変更の行の名前の列）で分けた成績の表。見出しの列名は ``label``。

    人気から見た差は、その節の全出走で数えた「同じ人気の馬の勝率・複勝率」からの差（pt）。穴馬だけの表でも、期待は
    節の全出走の人気ごとの率なので、6番人気の馬は6番人気の率と比べる。
    """

    title: str
    label: str
    column: str

    def used_columns(self) -> tuple[str, ...]:
        """この表を作るのに要る、出走の表の列。"""
        return (self.column, "popularity")

    def lines(self, runs: pd.DataFrame, tally: ReferenceTally) -> list[str]:
        return ["", f"### {self.title}", "", *self.body(runs, tally)]

    def body(self, runs: pd.DataFrame, tally: ReferenceTally) -> list[str]:
        expectation = PopularityExpectation(runs)
        rows = []
        for _, group in runs.dropna(subset=[self.column]).groupby(self.column, observed=True, sort=True):
            cells = tally.rows(group, (self.column,), (0,))[0]
            rows.append([*cells, gap_text(expectation.win_gap(group)), gap_text(expectation.top3_gap(group))])
        if not rows:
            return [EMPTY]
        header = [self.label, *PERF_HEADER, *GAP_HEADER]
        return ["| " + " | ".join(header) + " |", "| " + " | ".join([":---"] * len(header)) + " |",
                *("| " + " | ".join(row) + " |" for row in rows)]


def gap_text(gap: PopularityGap) -> str:
    """差を ``+1.2pt`` の形にする。数える出走が無ければ ``-``。"""
    return "-" if gap.runs == 0 else f"{gap.gap * 100:+.1f}pt"
