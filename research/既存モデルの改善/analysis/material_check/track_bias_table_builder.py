"""元の表にトラックバイアスの補正（まとまり U）の5列を足す。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.track_bias import BiasAttachment, BiasHistory, BiasRunRepository, RaceSlopes

#: 予想「展開から着順を予想」の置き場所の既定（展開の予想④ 4コーナーの位置の、年ごとの確かめの予測を読む）。
DEFAULT_DEVELOPMENT_ROOT = Path(__file__).resolve().parents[4] / "reports" / "展開から着順を予想"


class TrackBiasTableBuilder:
    """``prepare`` で元DB から中央・平地の全出走を読んでレースごとの傾きを出し（1分ほど）、``build`` で時点ごとの表に U を足す。

    U は予想のパッケージの ``BiasHistory``（その時点の展開の年ごとの確かめの予測④と、レースの年ごとに「その年より前のレースだけで作った
    過去の傾きの表」、そのレースより前に終わったレースの傾き）で、本番の学習と同じ計算で付ける。前日はその前の日の同じ馬場のレースだけ、
    当日はその日の先に終わったレースも数える。木曜は材料にしない。
    """

    def __init__(self, development_root: Path = DEFAULT_DEVELOPMENT_ROOT) -> None:
        self._history = BiasHistory(development_root)
        self._runs: pd.DataFrame | None = None
        self._slopes: pd.DataFrame | None = None

    def prepare(self, con: duckdb.DuckDBPyConnection) -> None:
        self._runs = BiasRunRepository(con).read()
        self._slopes = RaceSlopes().of(self._runs)

    def build(self, base: TrainingData, timing: PredictionTiming) -> TrainingData:
        if self._runs is None or self._slopes is None:
            raise RuntimeError("先に prepare で元DB を読んでください")
        return BiasAttachment().apply(base, self._history.of(timing, self._runs, self._slopes))
