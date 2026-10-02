"""基準のページの節に置く、「データマイニング予想の範囲」の段落の決まり。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 成績集計.reference_tally import ReferenceTally


@dataclass(frozen=True)
class MiningRangeSpec:
    """その節の、タイム型・対戦型の予想があるレースの数と期間。このあとの予想の表は、予想がある出走だけを数える。"""

    title: str = "データマイニング予想の範囲"

    def used_columns(self) -> tuple[str, ...]:
        """この段落を作るのに要る、出走の表の列。"""
        return ("dm_rank", "tm_rank")

    def lines(self, runs: pd.DataFrame, tally: ReferenceTally) -> list[str]:
        text = (f"タイム型 {_extent(runs[runs['dm_rank'].notna()])}、対戦型 {_extent(runs[runs['tm_rank'].notna()])}。"
                "次の表からは、予想がある出走だけを数える。")
        return ["", f"### {self.title}", "", text]


def _extent(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "なし"
    return f"{rows['rid'].nunique():,} レース（{rows['race_date'].min()}〜{rows['race_date'].max()}）"
