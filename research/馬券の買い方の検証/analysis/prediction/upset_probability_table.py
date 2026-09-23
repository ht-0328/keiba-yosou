"""荒れ具合の4つの確率を、人が読む表にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.workflow import BET, TOP_LEVEL, UPSET_OR_MORE


class UpsetProbabilityTable:
    """荒れ具合の4つの確率（行数 × 4。列はクラスの番号の順）を、券種・固い〜超荒れ・いちばん高いクラス・中荒れ以上の確率 の表にする。

    1レースの予測（``PredictionWorkflow._row``）と同じ列を、行数ぶんまとめて作る。中荒れ以上の確率は、固い以外の3つの合計。
    """

    def __init__(self, bet: BetType) -> None:
        self._bet = bet

    def build(self, probabilities: np.ndarray) -> pd.DataFrame:
        by_level = {level.label: probabilities[:, level.value] for level in UpsetLevel}
        top = [UpsetLevel(int(index)).label for index in probabilities.argmax(axis=1)]
        upset_or_more = probabilities[:, UpsetLevel.MID.value:].sum(axis=1)
        return pd.DataFrame({BET: self._bet.label, **by_level, TOP_LEVEL: top, UPSET_OR_MORE: upset_or_more})
