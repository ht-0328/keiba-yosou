"""能力指数の当たり具合（相関）が、なぜ変わったかを分けて見るための数を出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 共通.ability import ABILITY, FIELD_LEVEL, FIGURE, RUNS_USED

#: 近走を全部使えた走（使った走の数がこの数）だけのばらつきも出す。
_FULL_RUNS = 8


class AccuracyBreakdown:
    """``first``〜``last`` の開催日の走（能力指数の付いた走）で、相関と、相関を決める2つの量を出す。

    相関は「当てる相手の広がり」と「外れ方（ばらつき）」で決まる。ばらつきが同じでも、馬どうしの差（広がり）が
    小さくなれば、相関は下がる。例: どの馬も 5点ずつ外れるとき、馬どうしの差が 15点なら相関は高く、10点なら低い。

    - 相関・ばらつき: ``IndexAccuracy`` と同じ（ばらつき = その走の指数 − 能力指数 の標準偏差）。
    - 8走そろった走のばらつき: 近走を 8走とも使えた走だけのばらつき（使える近走の数の違いを除いたもの）。
    - 指数の広がり: その走のスピード指数の標準偏差。
    - クラスの間の広がり: レースの水準（クラスと年齢の組）ごとの指数の平均の、走で重み付けした標準偏差。
    - クラスの中の広がり: 水準ごとの平均を引いた残りの標準偏差。
    - 使った走の数の平均・1レースの頭数（指数の付いた走の数を、レースの数で割ったもの）。
    ``runs`` には ``FIELD_LEVEL`` の列が要る。
    """

    def score(self, runs: pd.DataFrame, first: str, last: str) -> dict[str, float]:
        dates = runs["race_date"]
        chosen = runs[dates.between(pd.Timestamp(first), pd.Timestamp(last)) & runs[FIGURE].notna() & runs[ABILITY].notna()]
        error = chosen[FIGURE] - chosen[ABILITY]
        level_mean = chosen.groupby(FIELD_LEVEL)[FIGURE].transform("mean")
        full = chosen[RUNS_USED] == _FULL_RUNS
        return {"走の数": len(chosen), "相関": float(np.corrcoef(chosen[ABILITY], chosen[FIGURE])[0, 1]),
                "ばらつき": float(error.std()), "8走そろった走のばらつき": float(error[full].std()),
                "指数の広がり": float(chosen[FIGURE].std()), "クラスの間の広がり": float(level_mean.std()),
                "クラスの中の広がり": float((chosen[FIGURE] - level_mean).std()),
                "使った走の数の平均": float(chosen[RUNS_USED].mean()),
                "1レースの頭数": float(len(chosen) / chosen["race_id"].nunique())}
