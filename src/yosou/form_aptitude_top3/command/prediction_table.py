"""予測の結果を表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from ..dataset import HORSE_NAME, HORSE_NO, RACE_DATE, RACE_ID
from ..feature import PredictionTiming
from ..ml_model import MEMBER_TYPES
from ..workflow import PROBABILITY
from .cell_format import day_text, horse_no_text, rounded


class PredictionTable:
    """予測の結果（1行 = 1頭）を、確率の高い順に並べた表にする。"""

    def __init__(self, prediction: pd.DataFrame, timing: PredictionTiming) -> None:
        self._prediction = prediction
        self._timing = timing
        self._member_names = [model_type.name for model_type in MEMBER_TYPES]

    def table(self) -> Table:
        ranked = self._prediction.sort_values(PROBABILITY, ascending=False, kind="stable")
        rows = [self._row(rank, runner) for rank, (_, runner) in enumerate(ranked.iterrows(), start=1)]
        return Table(
            ["順位", "馬番", "馬名", PROBABILITY, *self._member_names], rows,
            title=self._title(),
            note=f"{PROBABILITY}は {' と '.join(self._member_names)} の確率の平均。",
        )

    def _row(self, rank: int, runner: pd.Series) -> list[object]:
        member_cells = [rounded(runner[name]) for name in self._member_names]
        return [rank, horse_no_text(runner[HORSE_NO]), runner[HORSE_NAME],
                rounded(runner[PROBABILITY]), *member_cells]

    def _title(self) -> str:
        first_runner = self._prediction.iloc[0]
        race_day = day_text(first_runner[RACE_DATE])
        return f"{first_runner[RACE_ID]}（{race_day}）の予測: {self._timing.label}の時点"
