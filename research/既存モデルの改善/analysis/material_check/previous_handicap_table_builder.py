"""元の表に前走の不利（まとまり X）の5列を足す。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.review import HandicapHistory, PreviousHandicapAttachment, PreviousHandicapColumns, ReviewRunRepository
from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming


class PreviousHandicapTableBuilder:
    """``prepare`` で元DB から中央・平地の全出走を読み、出走ごとの不利（``HandicapHistory``。レースの年ごとに「その年より前のレースだけで作った
    表 G と過去の傾きの表」で判定）を出して、馬ごとに前走・前々走の値（``PreviousHandicapColumns``）にする（2分ほど）。
    ``build`` で時点ごとの表に X を足す（前走の結果から決まるので、どの時点でも同じ値）。"""

    def __init__(self) -> None:
        self._previous: pd.DataFrame | None = None

    def prepare(self, con: duckdb.DuckDBPyConnection) -> None:
        runs = ReviewRunRepository(con).read()
        self._previous = PreviousHandicapColumns().of(HandicapHistory().of(runs))

    def build(self, base: TrainingData, timing: PredictionTiming) -> TrainingData:
        if self._previous is None:
            raise RuntimeError("先に prepare で元DB を読んでください")
        return PreviousHandicapAttachment().apply(base, self._previous)
