"""組の表を、共有のモデルのクラスが受け取る形に詰め替える。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.dataset import BaselineLogit, PredictionData, TrainingData
from yosou.shared.feature import PredictionTiming

from ..feature import CATALOGS
from .column_names import BASELINE, COMBO, HIT, ODDS, PAYOUT, RACE_ID, WEIGHT

#: この予想の材料と出発点が分かる時点。券種のオッズの板が要るので、当日（締め切り前）。
TIMING = PredictionTiming.RACE_DAY
#: モデルに渡すときに ID として持つ列（どの組かを示すだけで、材料にしない）。
_ID_COLUMNS = [RACE_ID, COMBO]


class ModelDataFactory:
    """1つの券種の組の表を、学習データ（``TrainingData``）か予測用データ（``PredictionData``）に詰め替える。

    材料はその券種の一覧（``CATALOGS``）の列、目的変数は ``hit``、出発点（``baseline``）は市場の確率のロジット、
    行の重みは ``weight``（``MissSampling`` が付けた列。無ければ重みなし）。
    """

    def __init__(self, ticket_type: TicketType) -> None:
        self._catalog = CATALOGS[ticket_type]

    def training(self, table: pd.DataFrame) -> TrainingData:
        """学習・検証に使うデータ。``table`` は ``hit``・``payout`` の付いた組の表。"""
        weight = table[WEIGHT] if WEIGHT in table.columns else None
        return TrainingData(
            ids=table[_ID_COLUMNS], features=table[list(self._catalog.names)], targets=table[[HIT]],
            evaluation=table[[ODDS, PAYOUT]], catalog=self._catalog, label_name=HIT,
            baseline=BaselineLogit(table[BASELINE], TIMING), weight=weight,
        )

    def prediction(self, table: pd.DataFrame) -> PredictionData:
        """予測に使うデータ。``table`` は材料と出発点の付いた組の表（払戻は要らない）。"""
        return PredictionData(
            ids=table[_ID_COLUMNS], features=table[list(self._catalog.names)], timing=TIMING, catalog=self._catalog,
            baseline=BaselineLogit(table[BASELINE], TIMING),
        )
