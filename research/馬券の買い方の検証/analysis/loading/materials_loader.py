"""予測の CSV と事実表から材料表を作る。"""

from __future__ import annotations

from pathlib import Path

import duckdb

from ..prediction import PredictionFile
from ..prediction.prediction_sources import FAVORITES, FORM_APTITUDE, LONGSHOTS, UPSET_LEVEL
from ..race_material import RaceMaterials, RaceTableBuilder, RunnerTableBuilder
from ..repository import RaceDayRange, RaceFactRepository


class MaterialsLoader:
    """``predict_all.py`` が書いた4つの CSV（``<予測フォルダ>/<モデル名>.csv``）と、事実表のレースの属性から ``RaceMaterials`` を作る。

    事実表を読むのに元DB への接続が要る（接続ごとに1回、約20秒）。
    """

    def __init__(self, predictions_dir: Path, con: duckdb.DuckDBPyConnection) -> None:
        self._dir = Path(predictions_dir)
        self._con = con

    def load(self, days: RaceDayRange) -> RaceMaterials:
        form, favorites, longshots, upset = (self._read(name) for name in (FORM_APTITUDE, FAVORITES, LONGSHOTS, UPSET_LEVEL))
        runners = RunnerTableBuilder().build(form, favorites, longshots)
        races = RaceTableBuilder().build(runners, upset, RaceFactRepository(self._con).read(days))
        return RaceMaterials(races, runners).between(days.first_day, days.last_day)

    def _read(self, name: str):
        return PredictionFile(self._dir / f"{name}.csv").read()
