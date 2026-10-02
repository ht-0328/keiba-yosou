"""1つの出どころの成績。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..backtest import TOTAL_LABEL, PaybackSummary, PlaceLineStudy


@dataclass(frozen=True)
class SourceResult:
    """1つの出どころの確率で買ったときの成績。

    - ``name``: 出どころの名前（表の列の名前）。
    - ``study``: 線ごとの前半・後半の成績と、決まりで選んだ線。
    - ``bought``: 選んだ線で買った馬券（1行 = 1点。線が選べなければ空）。
    - ``yearly``: 選んだ線での年ごとの買い目・的中率・回収率・90% の幅（最後の行は合計）。
    """

    name: str
    study: PlaceLineStudy
    bought: pd.DataFrame
    yearly: pd.DataFrame

    @property
    def line(self) -> float | None:
        """決まりで選んだ線。選べなければ None。"""
        return None if self.study.chosen is None else self.study.chosen.line

    @property
    def late(self) -> PaybackSummary | None:
        """選んだ線での後半（線を選ぶのに使っていない期間）の成績。選べなければ None。"""
        return None if self.study.chosen is None else self.study.chosen.late

    @property
    def total_rate(self) -> float:
        """全期間の回収率（%）。買い目が無ければ NaN。"""
        return float(self._total_row()["回収率"])

    @property
    def total_low(self) -> float:
        """全期間の 90% の下限（%）。買い目が無ければ NaN。"""
        return float(self._total_row()["90%の下限"])

    def _total_row(self) -> pd.Series:
        return self.yearly[self.yearly["年"] == TOTAL_LABEL].iloc[0]
