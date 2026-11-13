"""人気薄が勝ったレースで、人気薄の中を並べたとき勝ち馬を上位何頭に置けたかの表（段1 の「人気薄の中の並べ方」と同じ形）。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..tables.cells import percent

TOP_KS: tuple[int, ...] = (1, 2, 3, 4)


@dataclass(frozen=True)
class OrderingCaptureTable:
    """``frame`` は ``EvaluationFrame`` の表。``orderings`` は並べ方に使う列の名前（大きい順に上に置く）。"""

    def build(self, frame: pd.DataFrame, orderings: Sequence[str], title: str) -> Table:
        won_races = frame.loc[frame["won"] == 1, "race_id"].unique()
        chosen = frame.loc[frame["race_id"].isin(won_races)]
        rows = [self._row(name, chosen) for name in orderings]
        size = chosen.groupby("race_id").size().mean() if len(chosen) else 0.0
        rows.append(["でたらめに選んだとき（目安）", *[percent(min(k, size), size) for k in TOP_KS]])
        return Table(["人気薄の中の並べ方", *[f"上位{k}頭に勝ち馬" for k in TOP_KS]], rows, title=title,
                     note=f"人気薄が勝ったレース {len(won_races)}。1レースの人気薄は平均 {size:.1f}頭。")

    @staticmethod
    def _row(name: str, chosen: pd.DataFrame) -> list[object]:
        rank = chosen[name].groupby(chosen["race_id"]).rank(ascending=False, method="first")
        winners = rank[chosen["won"] == 1]
        return [name, *[percent((winners <= k).sum(), len(winners)) for k in TOP_KS]]
