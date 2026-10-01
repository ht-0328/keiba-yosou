"""基準のページの節に置く、「値ごとに小見出しを立てて、その中に成績の表を置く」表の決まり（クラス別 × 人気 など）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 成績集計.reference_table_spec import EMPTY, ReferenceTableSpec
from 成績集計.reference_tally import ReferenceTally, label_text


@dataclass(frozen=True)
class ReferenceGroupSpec:
    """``group_column`` の値ごとに ``#### 値`` を立て、その値の出走で ``inner`` の表を作る。

    クラス・頭数・月はレースの属性なので、全馬で率を出すと勝率が 1÷頭数 になる。そのため中の表は人気などで分ける。
    小見出しは、中の表に数える出走がある値だけ（値の順）。
    """

    title: str
    group_column: str
    inner: ReferenceTableSpec

    def used_columns(self) -> tuple[str, ...]:
        """この表を作るのに要る、出走の表の列。"""
        return (self.group_column, *self.inner.columns)

    def lines(self, runs: pd.DataFrame, tally: ReferenceTally) -> list[str]:
        counted = runs.dropna(subset=[self.group_column, *self.inner.columns])
        lines = ["", f"### {self.title}"]
        for value, group in counted.groupby(self.group_column, observed=True, sort=True):
            lines.extend(["", f"#### {label_text(value)}", "", *self.inner.body(group, tally)])
        return lines if len(lines) > 2 else [*lines, "", EMPTY]
