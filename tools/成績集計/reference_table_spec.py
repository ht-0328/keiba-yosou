"""基準のページの節（コース×馬場状態）に置く、成績の表1つの決まり。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 成績集計.reference_tally import PERF_HEADER, ReferenceTally

EMPTY = "該当なし"


@dataclass(frozen=True)
class ReferenceTableSpec:
    """``columns``（``ReferenceRuns``・``ReferenceLabels`` の列）で分けた成績の表。見出しの列名は ``labels``。

    ``shown`` は表に出す ``columns`` の番号（省略で全部）。``top`` があれば、出走 ``min_runs`` 以上の値のうち勝率の上位
    ``top`` 件だけ出す。
    """

    title: str
    labels: tuple[str, ...]
    columns: tuple[str, ...]
    shown: tuple[int, ...] | None = None
    top: int | None = None
    min_runs: int = 0

    def used_columns(self) -> tuple[str, ...]:
        """この表を作るのに要る、出走の表の列。"""
        return self.columns

    def lines(self, runs: pd.DataFrame, tally: ReferenceTally) -> list[str]:
        return ["", f"### {self.title}", "", *self.body(runs, tally)]

    def body(self, runs: pd.DataFrame, tally: ReferenceTally) -> list[str]:
        shown = self.shown if self.shown is not None else tuple(range(len(self.columns)))
        if self.top is None:
            rows = tally.rows(runs, self.columns, shown)
        else:
            rows = tally.top_rows(runs, self.columns, shown, top=self.top, min_runs=self.min_runs)
        return markdown_table(self.labels, rows) if rows else [EMPTY]


def markdown_table(labels: tuple[str, ...], rows: list[list[str]]) -> list[str]:
    header = [*labels, *PERF_HEADER]
    return ["| " + " | ".join(header) + " |", "| " + " | ".join([":---"] * len(header)) + " |",
            *("| " + " | ".join(row) + " |" for row in rows)]
