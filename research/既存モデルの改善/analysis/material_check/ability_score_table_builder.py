"""元の表に能力スコア（まとまり T）の4列を足す。"""

from __future__ import annotations

import duckdb

from yosou.ability_score import AbilityScoreAttachment
from yosou.shared.dataset import TrainingData
from yosou.shared.feature import PredictionTiming


class AbilityScoreTableBuilder:
    """T は、元の表にもうある能力指数（M の「指数_条件の重み」。レースより前の走から作ったもの）と今回の斤量から出すので、
    元DB も外の表も要らない。予想のパッケージの ``AbilityScoreAttachment`` で、本番と同じ計算で足す。"""

    def prepare(self, con: duckdb.DuckDBPyConnection) -> None:
        return None

    def build(self, base: TrainingData, timing: PredictionTiming) -> TrainingData:
        return AbilityScoreAttachment().apply(base)
