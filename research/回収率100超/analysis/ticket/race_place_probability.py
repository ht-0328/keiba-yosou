"""3着以内の確率を、レースの中でつじつまが合うようにそろえ直す。"""

from __future__ import annotations

import numpy as np
import pandas as pd


class RacePlaceProbability:
    """1頭ずつ出した「3着以内に入る確率」を、レース内で合計が対象頭数になるようそろえ直す。

    1頭ずつ独立に学習すると、同じレースの確率を足しても 3（5〜7頭立てなら 2）にならない。
    たとえば「全頭が 3着以内に入りそうなレース」という、ありえない形になることがある。
    足して 3 にそろえると、同じレースの馬どうしの相対が正しくなる。

    実測では、そろえ直したほうが期待値で選んだ買い目の回収率が上がった。
    """

    def normalize(self, probability: pd.Series, race: pd.Series, places: pd.Series) -> pd.Series:
        """``places`` は複勝の対象着順（5〜7頭立ては 2、8頭以上は 3）。"""
        total = probability.groupby(race).transform("sum")
        scaled = probability * places / total.replace(0, np.nan)
        return scaled.clip(lower=1e-9, upper=1.0)
