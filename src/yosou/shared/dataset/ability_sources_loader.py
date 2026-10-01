"""馬の力の材料（まとまり M）の元の記録を集める。"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from ..feature.ability import AbilitySources
from ..repository import (
    AbilityRunRepository,
    SalePriceRepository,
    SpeedFigureRepository,
    TargetScope,
    WorkoutSummaryRepository,
)
from ..repository.speed_figure_repository import DEFAULT_FOLDER

#: 過去の出走を読む最初の日（DB にある最初の年）。通算の成績は、この日から数える。
HISTORY_FIRST_DAY = date(2011, 1, 1)


class AbilitySourcesLoader:
    """リポジトリを順に呼んで、馬の力の材料の元の記録（``AbilitySources``）を集める。SQL は持たない。

    ``figure_folder`` はスピード指数をとっておく場所（省略すると道具「能力指数」と同じ ``reports/能力指数/cache/``。
    テストでは一時フォルダを渡す）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, figure_folder: Path = DEFAULT_FOLDER) -> None:
        self._runs = AbilityRunRepository(con, HISTORY_FIRST_DAY)
        self._figures = SpeedFigureRepository(con, figure_folder)
        self._workouts = WorkoutSummaryRepository(con)
        self._sales = SalePriceRepository(con)

    def load(self, scope: TargetScope) -> AbilitySources:
        """``scope`` の出走と、その前の全出走の記録。"""
        return AbilitySources(runs=self._runs.read(scope), figures=self._figures.read(),
                              workouts=self._workouts.read(scope), sales=self._sales.read())
