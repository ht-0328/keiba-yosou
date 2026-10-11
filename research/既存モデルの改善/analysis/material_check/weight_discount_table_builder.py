"""元の表に馬体重の表の割引（まとまり V）の列を足す。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.weight_table import WeightRunRepository, WeightRuns, YearlyWeightDiscount


class WeightDiscountTableBuilder:
    """``prepare`` で元DB から中央・平地の全出走を読んで表の材料（帯・市場から見た3着以内率・3着以内）を作り（1分ほど）、
    ``build`` で当日の表に V を足す。V は予想のパッケージの ``YearlyWeightDiscount``（レースの年ごとに「その年より前のレースだけで作った
    表 W」を、元の表の増減・前走からの日数・馬齢で引く）で、本番の学習と同じ計算で付ける。"""

    def __init__(self) -> None:
        self._prepared: pd.DataFrame | None = None

    def prepare(self, con: duckdb.DuckDBPyConnection) -> None:
        self._prepared = WeightRuns().build(WeightRunRepository(con).read())

    def build(self, base: TrainingData, timing: PredictionTiming) -> TrainingData:
        if self._prepared is None:
            raise RuntimeError("先に prepare で元DB を読んでください")
        return YearlyWeightDiscount().apply(base, self._prepared)
