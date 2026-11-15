"""券種ごとに、選ぶ年の数え上げから形を1つ選ぶ（設計書 16 の 6.4）。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from 全レース全券種の買い方.analysis.recovery_bootstrap import RecoveryBootstrap

from .shape_counter import POINTS, RETURN, SHAPE
from .ticket_shape import TicketShape

#: 当たった重賞の数の下限（重賞は数が少ないので、全レースの研究の 30 から 15 に下げる）。
MIN_HIT_RACES = 15
#: 1点の額（円）。
UNIT = 100


class ShapeChooser:
    """形ごとの数え上げ（``ShapeCounter.count``）の、選ぶ年の行だけから、券種ごとに形を1つ選ぶ。

    当たった重賞が ``MIN_HIT_RACES`` 以上の形のうち、回収率の 90% の幅の下の端（開催日を単位にしたブートストラップ）がいちばん高い形。
    その数の形が無い券種は、全部の形の中で下の端がいちばん高い形。
    """

    def summary(self, counts: pd.DataFrame, shapes: Sequence[TicketShape]) -> pd.DataFrame:
        """形ごとの成績（1行 = 形）。列 shape・ticket・name・races（買った重賞）・hits（当たった重賞）・points・stake・return・rate・lower。"""
        bought = counts[counts[POINTS] > 0]
        days = sorted(counts["race_date"].unique())
        position = {day: index for index, day in enumerate(days)}
        boot = RecoveryBootstrap(len(days))
        stakes = np.zeros((len(shapes), len(days)))
        returns = np.zeros((len(shapes), len(days)))
        columns = bought["race_date"].map(position).to_numpy()
        np.add.at(stakes, (bought[SHAPE].to_numpy(), columns), bought[POINTS].to_numpy() * UNIT)
        np.add.at(returns, (bought[SHAPE].to_numpy(), columns), bought[RETURN].to_numpy())
        lower = boot.lower(stakes, returns)
        grouped = bought.groupby(SHAPE)
        races = grouped.size().reindex(range(len(shapes)), fill_value=0)
        hits = grouped[RETURN].apply(lambda values: int((values > 0).sum())).reindex(range(len(shapes)), fill_value=0)
        points = grouped[POINTS].sum().reindex(range(len(shapes)), fill_value=0)
        stake, payback = stakes.sum(axis=1), returns.sum(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            rate = np.where(stake > 0, payback / stake, np.nan)
        return pd.DataFrame({
            SHAPE: range(len(shapes)), "ticket": [shape.ticket for shape in shapes], "name": [shape.name for shape in shapes],
            "races": races.to_numpy(), "hits": hits.to_numpy(), "points": points.to_numpy(), "stake": stake, "return": payback,
            "rate": rate, "lower": lower,
        })

    def choose(self, summary: pd.DataFrame) -> dict[str, int]:
        """券種 → 選んだ形の番号。"""
        chosen = {}
        for ticket, group in summary.groupby("ticket", sort=False):
            enough = group[group["hits"] >= MIN_HIT_RACES]
            pool = enough if len(enough) else group
            pool = pool[pool["lower"].notna()]
            if len(pool):
                chosen[ticket] = int(pool.sort_values(["lower", "rate"], ascending=False)[SHAPE].iloc[0])
        return chosen
