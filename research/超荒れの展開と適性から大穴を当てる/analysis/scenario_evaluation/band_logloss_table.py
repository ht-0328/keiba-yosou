"""人気帯ごとに、3着以内と1着の確率の当たり具合（対数損失）を、予想ごと・期間ごとに市場と並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

from .evaluation_frame import CONFIRM, EXPLORE
from .popularity_band import PopularityBand

_EDGE = 1e-6
_NOTE = ("対数損失 = −（実際 × log 確率 ＋（1 − 実際）× log（1 − 確率））の平均。小さいほど確率がよく当たっている。"
         "市場との差がマイナスなら、市場（オッズから見た率）より当たっている。どの予想も、その予想の確率がある行だけで、同じ行の市場と比べる。")


def _loss(probability: pd.Series, actual: pd.Series) -> float:
    p = probability.clip(_EDGE, 1 - _EDGE)
    return float(-(actual * np.log(p) + (1 - actual) * np.log(1 - p)).mean())


@dataclass(frozen=True)
class BandLoglossTable:
    """``frame`` は ``EvaluationFrame`` の表。``sources`` は予想の名前の並び。"""

    bands: tuple[PopularityBand, ...]
    sources: tuple[str, ...]

    def build(self, frame: pd.DataFrame, target: str, title: str) -> Table:
        rows = []
        for band in self.bands:
            members = frame.loc[band.contains(frame["popularity"])]
            for source in self.sources:
                column = f"p_{target}_{source}"
                if column not in members:
                    continue
                for period in (EXPLORE, CONFIRM):
                    part = members.loc[(members["period"] == period) & members[column].notna()]
                    if part.empty:
                        continue
                    model, market = _loss(part[column], part[f"y_{target}"]), _loss(part[f"m_{target}"], part[f"y_{target}"])
                    rows.append([band.name, source, period, len(part), f"{model:.5f}", f"{market:.5f}", f"{model - market:+.5f}",
                                 f"{part[column].mean():.4f}", f"{part[f'y_{target}'].mean():.4f}"])
        columns = ["人気帯", "予想", "期間", "頭数", "対数損失", "市場の対数損失", "市場との差", "確率の平均", "実際の割合"]
        return Table(columns, rows, title=title, note=_NOTE)
