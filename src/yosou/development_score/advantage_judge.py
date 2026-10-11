"""展開スコアを、展開有利・展開不利・どちらでもないに分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import names

#: 有利・不利の線（3着以内の確率のポイント。設計書 05 の 2）。道具「展開スコア」の ``line_check.py`` で決めた: ±0.02 では判定される馬が
#: ごく少なく年ごとの向きが安定しないが、±0.01 なら有利側・不利側とも全ての年で「実際の3着以内率 − 市場の見立て」の向きが合う。
DEFAULT_LINE = 0.01


class AdvantageJudge:
    """D が ``line`` 以上なら展開有利、``−line`` 以下なら展開不利、そのあいだはどちらでもない（「－」）。D が欠損値なら欠損値。"""

    def __init__(self, line: float = DEFAULT_LINE) -> None:
        if line <= 0:
            raise ValueError(f"線は正の値にします: {line}")
        self._line = line

    @property
    def line(self) -> float:
        return self._line

    def of(self, score: pd.Series) -> pd.Series:
        """行ごとの判定。index は ``score`` と同じ。"""
        verdict = np.select([score >= self._line, score <= -self._line, score.notna()],
                            [names.FAVORED, names.UNFAVORED, names.NEUTRAL], default=None)
        return pd.Series(verdict, index=score.index, dtype="object")
