"""荒れるレースの判定。"""

from __future__ import annotations

import pandas as pd

from yosou.upset_level.dataset import BetType

from ..column_names import upset_column


class UpsetJudge:
    """荒れ具合モデルの「中荒れ以上の確率」（券種ごと）で、荒れるレースかを決める。

    ``threshold`` が None なら、どのレースも荒れないとみなす（荒れ判定を使わないパターン用）。
    ``scores`` は、毎週の上位 k を選ぶときの順位付けに使う点（確率そのもの）。
    """

    def __init__(self, threshold: float | None) -> None:
        self._threshold = threshold

    @property
    def threshold(self) -> float | None:
        return self._threshold

    def scores(self, races: pd.DataFrame, bet: BetType) -> pd.Series:
        return races[upset_column(bet)]

    def is_upset(self, races: pd.DataFrame, bet: BetType) -> pd.Series:
        if self._threshold is None:
            return pd.Series(False, index=races.index)
        return (self.scores(races, bet) >= self._threshold).fillna(False)
