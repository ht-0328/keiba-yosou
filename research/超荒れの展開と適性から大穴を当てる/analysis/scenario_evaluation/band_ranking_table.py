"""人気帯（中穴・大穴）の馬が勝ったレースで、その人気帯の中を並べたとき、勝ち馬を上位何頭に置けたかと、
荒れる前提の確率（その人気帯の中で合計 1 にそろえた1着の確率）の対数損失を、予想ごと・期間ごとに並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

from ..tables.cells import percent
from .evaluation_frame import CONFIRM, EXPLORE
from .popularity_band import PopularityBand

_EDGE = 1e-6
_NOTE = ("「人気の順」は単勝オッズの小さい順。どの予想も、その予想の確率がその人気帯の全部の馬にあるレースだけで数え、同じレースでの人気の順を横に並べる。"
         "荒れる前提の対数損失 = −log（勝ち馬の確率 ÷ その人気帯の確率の合計）の平均。小さいほど良い。市場は単勝オッズから見た勝率。")


@dataclass(frozen=True)
class BandRankingTable:
    """``frame`` は ``EvaluationFrame`` の表。``sources`` は予想の名前の並び（列 ``p_win_<名前>`` を使う）。"""

    band: PopularityBand
    sources: tuple[str, ...]

    def build(self, frame: pd.DataFrame, title: str) -> Table:
        rows = []
        for source in self.sources:
            column = f"p_win_{source}"
            if column not in frame:
                continue
            for period in (EXPLORE, CONFIRM):
                rows.append(self._row(frame.loc[frame["period"] == period], source, column, period))
        columns = ["予想", "期間", "レース数", "上位1頭", "上位3頭", "人気の順の上位1頭", "人気の順の上位3頭", "荒れる前提の対数損失", "市場の対数損失"]
        return Table(columns, [row for row in rows if row], title=title, note=_NOTE)

    def _row(self, part: pd.DataFrame, source: str, column: str, period: str) -> list[object] | None:
        members = part.loc[self.band.contains(part["popularity"])]
        won = members.groupby("race_id")["y_win"].transform("sum") > 0
        complete = members.groupby("race_id")[column].transform(lambda values: values.notna().all())
        races = members.loc[won & complete]
        if races.empty:
            return None
        winners = races["y_win"] > 0
        model_rank = races.groupby("race_id")[column].rank(ascending=False, method="first")
        market_rank = races.groupby("race_id")["m_win"].rank(ascending=False, method="first")
        share = races[column] / races.groupby("race_id")[column].transform("sum")
        market_share = races["m_win"] / races.groupby("race_id")["m_win"].transform("sum")
        count = int(winners.sum())
        return [source, period, count, percent((model_rank[winners] <= 1).sum(), count), percent((model_rank[winners] <= 3).sum(), count),
                percent((market_rank[winners] <= 1).sum(), count), percent((market_rank[winners] <= 3).sum(), count),
                f"{-np.log(share[winners].clip(_EDGE)).mean():.4f}", f"{-np.log(market_share[winners].clip(_EDGE)).mean():.4f}"]
