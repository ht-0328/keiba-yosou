"""人気薄が勝ったレースで、人気薄の中をどう並べれば勝ち馬を上位に置けたかの表（今のモデル・人気・上乗せ・型の数）。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..theory.runner_type_catalog import RUNNER_TYPES
from .cells import percent

#: 上位何頭までを見るか。
TOP_KS: tuple[int, ...] = (1, 2, 3, 4)


def _type_score(x: pd.DataFrame) -> pd.Series:
    """当てはまる型の数を先に、同じ数ならオッズから見た勝率の高い順にする点数。"""
    count = sum(x[rule.name].astype(int) for rule in RUNNER_TYPES)
    return count * 10 + x["market"]


#: 並べ方（名前 → 大きいほど上に置く値）。
ORDERINGS: dict[str, Callable[[pd.DataFrame], pd.Series]] = {
    "今のモデルの1着の確率の順": lambda x: x["model"],
    "人気の順（オッズから見た勝率の順）": lambda x: x["market"],
    "上乗せの順": lambda x: x["uplift"],
    "当てはまる型の数の順": _type_score,
}


@dataclass(frozen=True)
class LongshotRankTable:
    """``longshots`` は人気薄の馬の行（型の列は ``RunnerTypeFlags`` が足したもの）。人気薄が勝ち、今のモデルの予測があるレースだけを見る。"""

    def build(self, longshots: pd.DataFrame, title: str) -> Table:
        known = longshots.loc[longshots.groupby("race_id")["model"].transform(lambda s: s.notna().all())]
        races = known.loc[known["finish"] == 1, "race_id"].unique()
        chosen = known.loc[known["race_id"].isin(races)]
        size = chosen.groupby("race_id").size().mean() if len(chosen) else 0.0
        rows = [self._row(name, order, chosen) for name, order in ORDERINGS.items()]
        rows.append(["でたらめに選んだとき（目安）", *[percent(min(k, size), size) for k in TOP_KS]])
        return Table(["人気薄の中の並べ方", *[f"上位{k}頭に勝ち馬" for k in TOP_KS]], rows, title=title,
                     note=f"対象は人気薄が勝ったレース {len(races)}。1レースの人気薄は平均 {size:.1f}頭。")

    @staticmethod
    def _row(name: str, order: Callable[[pd.DataFrame], pd.Series], chosen: pd.DataFrame) -> list[object]:
        rank = order(chosen).groupby(chosen["race_id"]).rank(ascending=False, method="first")
        winners = rank[chosen["finish"] == 1]
        return [name, *[percent((winners <= k).sum(), len(winners)) for k in TOP_KS]]
