"""能力指数が、その走のスピード指数をどれだけ当てるか。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通.ability import ABILITY, FIGURE


class IndexAccuracy:
    """``first``〜``last`` の開催日の走で、能力指数（その走より前の走だけから作ったもの）と、その走のスピード指数を比べる。

    - 相関: 能力指数とスピード指数の相関。1 に近いほど、能力指数の高い馬が実際に速く走った。
    - 誤差: スピード指数 − 能力指数 の平均（ずれ）と、平均を引いたあとの標準偏差（ばらつき）。
    - 付いた割合: スピード指数のある走のうち、能力指数が付いた（使える過去の走があった）割合。
    着順は使わない。タイムから作ったスピード指数だけで比べる。
    """

    def score(self, runs: pd.DataFrame, first: str, last: str) -> dict[str, float]:
        chosen = runs["race_date"].between(pd.Timestamp(first), pd.Timestamp(last)) & runs[FIGURE].notna()
        target = runs.loc[chosen, FIGURE]
        index = runs.loc[chosen, ABILITY]
        paired = index.notna()
        error = (target - index)[paired]
        return {"走の数": int(paired.sum()), "付いた割合": float(paired.mean() * 100),
                "相関": float(np.corrcoef(index[paired], target[paired])[0, 1]),
                "ずれ": float(error.mean()), "ばらつき": float(error.std())}
