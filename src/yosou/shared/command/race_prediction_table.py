"""レース単位の予測の結果を表にする。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 共通.render import Table

from ..dataset import RACE_DATE, RACE_ID
from ..feature import PredictionTiming
from .cell_format import day_text, rounded


class RacePredictionTable:
    """レース単位の予測の結果（1行 = 1つの見方。荒れ具合の予想では券種）を、そのまま表にする。

    ``columns`` は出す列の名前の並び（予想ごと。例: 券種・固い・中荒れ・大荒れ・超荒れ・いちばん高いクラス・中荒れ以上の確率）。
    小数は3桁に丸め、文字はそのまま出す。
    """

    def __init__(self, prediction: pd.DataFrame, timing: PredictionTiming, columns: Sequence[str],
                 note: str = "") -> None:
        self._prediction = prediction
        self._timing = timing
        self._columns = tuple(columns)
        self._note = note

    def table(self) -> Table:
        rows = [self._row(row) for _, row in self._prediction.iterrows()]
        return Table(list(self._columns), rows, title=self._title(), note=self._note)

    def _row(self, row: pd.Series) -> list[object]:
        return [self._cell(row[name]) for name in self._columns]

    def _cell(self, value: object) -> object:
        if isinstance(value, float):
            return rounded(value)
        return value

    def _title(self) -> str:
        first = self._prediction.iloc[0]
        return f"{first[RACE_ID]}（{day_text(first[RACE_DATE])}）の予測: {self._timing.label}の時点"
