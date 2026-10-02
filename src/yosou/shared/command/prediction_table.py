"""予測の結果を表にする。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 共通.render import Table

from ..dataset import HORSE_NAME, HORSE_NO, RACE_DATE, RACE_ID
from ..feature import PredictionTiming
from ..ml_model import MEMBER_TYPES
from .cell_format import day_text, horse_no_text, rounded


class PredictionTable:
    """予測の結果（1行 = 1頭）を、確率の高い順に並べた表にする。

    ``probability`` は確率の列の名前（予想ごとに違う。例: 3着以内に入る確率）。
    ``extra_columns`` は、馬名のあとに足す列の名前（予想ごとに違う。例: 人気順位）。
    """

    def __init__(self, prediction: pd.DataFrame, timing: PredictionTiming, probability: str,
                 extra_columns: Sequence[str] = ()) -> None:
        self._prediction = prediction
        self._timing = timing
        self._probability = probability
        self._extra_columns = tuple(extra_columns)
        self._member_names = [model_type.name for model_type in MEMBER_TYPES]

    def table(self) -> Table:
        ranked = self._prediction.sort_values(self._probability, ascending=False, kind="stable")
        rows = [self._row(rank, runner) for rank, (_, runner) in enumerate(ranked.iterrows(), start=1)]
        return Table(
            ["順位", "馬番", "馬名", *self._extra_columns, self._probability, *self._member_names], rows,
            title=self._title(),
            note=f"{self._probability}は {' と '.join(self._member_names)} の確率の平均。",
        )

    def _row(self, rank: int, runner: pd.Series) -> list[object]:
        extra_cells = [self._cell(runner[name]) for name in self._extra_columns]
        member_cells = [rounded(runner[name]) for name in self._member_names]
        return [rank, horse_no_text(runner[HORSE_NO]), runner[HORSE_NAME], *extra_cells,
                rounded(runner[self._probability]), *member_cells]

    def _cell(self, value: object) -> object:
        """足す列の値。小数は3桁に丸め、文字はそのまま出す。"""
        if isinstance(value, float):
            return rounded(value)
        return value

    def _title(self) -> str:
        first_runner = self._prediction.iloc[0]
        race_day = day_text(first_runner[RACE_DATE])
        return f"{first_runner[RACE_ID]}（{race_day}）の予測: {self._timing.label}の時点"
