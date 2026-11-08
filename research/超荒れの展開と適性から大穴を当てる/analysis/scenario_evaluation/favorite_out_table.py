"""人気馬（1〜3番人気）が4着以下になる確率の当たり具合と、市場の見立てより4着以下になりやすいと見た馬の実際を、予想ごとに並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from 共通.render import Table

from ..tables.cells import percent
from .evaluation_frame import CONFIRM, EXPLORE

_EDGE = 1e-6
_NOTE = ("4着以下になる確率: 新しい予想は 1 − 3着以内の確率、今の消は予想「人気馬が4着以下になるかを予想」の確率、市場は 1 − オッズから見た3着以内率。"
         "市場との差 = 予想の4着以下の確率 − 市場の4着以下の確率。差の大きい順に上位1割の馬（市場の見立てより負けやすいと見た馬）の、実際の4着以下の割合と、"
         "同じ馬の市場の見立て（4着以下の確率の平均）を並べる。実際が見立てより大きいほど、危険な人気馬をよく見つけている。")


@dataclass(frozen=True)
class FavoriteOutTable:
    """``frame`` は ``EvaluationFrame`` の表に、今の消の確率の列 ``out_current`` を足したもの。"""

    def build(self, frame: pd.DataFrame, sources: dict[str, str], title: str) -> Table:
        rows = []
        favorites = frame.loc[frame["popularity"] <= 3].copy()
        favorites["out_actual"] = 1.0 - favorites["y_top3"]
        favorites["out_market"] = 1.0 - favorites["m_top3"]
        for name, column in sources.items():
            for period in (EXPLORE, CONFIRM):
                part = favorites.loc[(favorites["period"] == period) & favorites[column].notna()]
                if part.empty:
                    continue
                edge = part[column] - part["out_market"]
                top = part.loc[edge >= edge.quantile(0.9)]
                rows.append([name, period, len(part), f"{self._loss(part[column], part['out_actual']):.5f}",
                             f"{self._loss(part['out_market'], part['out_actual']):.5f}", len(top),
                             percent(top["out_actual"].sum(), len(top)), f"{top['out_market'].mean() * 100:.1f}%",
                             f"{(top['out_actual'].mean() - top['out_market'].mean()) * 100:+.2f}"])
        columns = ["予想", "期間", "人気馬の頭数", "対数損失", "市場の対数損失", "上位1割の頭数", "上位1割の実際の4着以下", "上位1割の市場の見立て",
                   "実際 − 見立て（ポイント）"]
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _loss(probability: pd.Series, actual: pd.Series) -> float:
        p = probability.clip(_EDGE, 1 - _EDGE)
        return float(-(actual * np.log(p) + (1 - actual) * np.log(1 - p)).mean())
