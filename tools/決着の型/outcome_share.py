"""決着の切り口ごとに、レース数と割合を数える。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 共通.render import Table

from 決着の型.outcome_dimension import OutcomeDimension

COLUMNS: tuple[str, ...] = ("レース数", "割合")


class OutcomeShare:
    """決着の表を切り口（1つ以上）で分け、値ごとのレース数と割合を出す。

    切り口が1つなら、割合は全レースに対するもの。2つ以上なら、最後の切り口が「何を数えるか」、前の切り口が「どう分けるか」で、
    割合は前の切り口の値が同じレースの中で数える（``year top5-mix`` なら、年ごとの中での決着の組の割合）。
    """

    def __init__(self, dimensions: Sequence[OutcomeDimension]) -> None:
        if not dimensions:
            raise ValueError("切り口を1つ以上指定してください（--list で一覧）")
        self._dimensions = tuple(dimensions)

    def count(self, races: pd.DataFrame) -> pd.DataFrame:
        """値の組ごとのレース数と割合（0〜1）。値の並びは切り口の目録の順（目録に無い値はその値の順）。"""
        titles = [dim.title for dim in self._dimensions]
        frame = pd.DataFrame({dim.title: dim.values(races) for dim in self._dimensions}, index=races.index)
        counted = frame.value_counts(sort=False).rename("races").reset_index()
        group_titles = titles[:-1]
        denominator = counted.groupby(group_titles)["races"].transform("sum") if group_titles else counted["races"].sum()
        counted["share"] = counted["races"] / denominator
        counted["_order"] = [tuple((dim.order(value), value) for dim, value in zip(self._dimensions, row))
                             for row in counted[titles].itertuples(index=False)]
        return counted.sort_values("_order").drop(columns="_order").reset_index(drop=True)

    def table(self, races: pd.DataFrame, condition: str) -> Table:
        """表（切り口の列 + レース数 + 割合）。見出しに条件と期間・レース数を書く。"""
        counted = self.count(races)
        titles = [dim.title for dim in self._dimensions]
        rows = [[*(row[title] for title in titles), int(row["races"]), f"{row['share'] * 100:.1f}%"] for _, row in counted.iterrows()]
        span = f"{races['race_date'].min()}〜{races['race_date'].max()}、{len(races):,} レース" if len(races) else "該当なし"
        basis = f"割合は「{titles[-2]}」の値が同じレースの中で。" if len(titles) > 1 else "割合は全レースに対して。"
        table = Table([*titles, *COLUMNS], rows, title=f"{'×'.join(titles)} — {condition}（{span}）",
                      note=" ".join(dict.fromkeys([basis, *(dim.note for dim in self._dimensions if dim.note)])))
        table.meta = {"dimensions": [dim.name for dim in self._dimensions], "races": int(len(races)), "condition": condition}
        return table
