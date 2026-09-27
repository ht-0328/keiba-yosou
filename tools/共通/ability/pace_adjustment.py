"""ペース補正の大きさを、タイムから測る。"""

from __future__ import annotations

import pandas as pd

from .pace_balance import PACE
from .speed_figure import FIGURE

#: 馬のふだんの指数を出すのに要る走の数。
_MIN_RUNS = 3
#: 指数の点数を % に戻す割り算。
_POINTS_PER_PERCENT = 10.0


class PaceAdjustment:
    """（脚質, ペース）ごとに、その走が馬のふだんの指数より何%高かったか・低かったかの平均を出す。

    ペース補正をかけていないスピード指数を受け取り、馬ごとに「その走の指数 − その馬の指数の平均」を出して、
    脚質（JV-Data の脚質判定）とペース（``PaceBalance``）の組ごとに平均する。同じ馬どうしで比べるので、
    馬の力の違いは消え、展開で得をした分・損をした分が残る。
    例: スローで逃げた走が、同じ馬のふだんより平均 0.3% 速ければ、（逃げ, スロー）の補正は 0.3（その分を引く）。
    走が 3回に満たない馬は使わない。
    """

    def fit(self, runs: pd.DataFrame) -> pd.Series:
        figure = runs[FIGURE] / _POINTS_PER_PERCENT
        counted = figure.groupby(runs["horse_id"]).transform("count")
        usable = figure.notna() & (counted >= _MIN_RUNS) & runs[PACE].notna() & runs["style"].notna()
        residual = (figure - figure.groupby(runs["horse_id"]).transform("mean"))[usable]
        return residual.groupby([runs.loc[usable, "style"], runs.loc[usable, PACE]]).mean()
