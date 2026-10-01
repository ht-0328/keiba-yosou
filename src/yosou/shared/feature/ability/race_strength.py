"""レースの強さ（そのレースに出た馬の力の高さ）を数える。"""

from __future__ import annotations

import pandas as pd

#: 強さを数えるのに使う、力の上位の頭数。
_TOP = 5
#: 力の列（``SpeedFigureHistory`` が作る「そのレースの時点の力」）。
_POWER = "指数_条件の重み"


class RaceStrength:
    """レースごとの強さ = 出走した馬の「そのレースの時点の力」（指数_条件の重み）の上位 5頭の平均。

    過去走の「相手の強さ」に使う。例: 上位5頭の力が 84・82・80・79・75 なら 80。
    ``runs`` は出走した馬の行（race_id・horse_id）、``figures`` は ``SpeedFigureHistory`` の結果。
    """

    def of(self, runs: pd.DataFrame, figures: pd.DataFrame) -> pd.Series:
        """レースID → 強さ。"""
        runners = runs[["race_id", "horse_id"]].merge(figures[["race_id", "horse_id", _POWER]], on=["race_id", "horse_id"])
        top = runners.sort_values(_POWER, ascending=False).groupby("race_id").head(_TOP)
        return top.groupby("race_id")[_POWER].mean()
