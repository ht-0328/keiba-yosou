"""これから走る1レースの予測用データに、バイアスの補正を足す（予測の流れに渡す関数の形）。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.dataset import OddsInput, PredictionData
from yosou.shared.feature import PredictionTiming

from .bias_attachment import BiasAttachment
from .prior_slope_table import PriorSlopeTable
from .race_bias_source import PaceForecast, RaceBiasSource


class RaceBiasAttacher:
    """``RaceBiasSource`` で作ったバイアスの補正の表を、予測用データに ``BiasAttachment`` で足す。

    全頭の予想の予測の流れ（``PredictionWorkflow``）の ``extras``・``win_extras`` に渡す関数の形（``attach``）。
    同じレース・同じ時点で続けて呼ばれたら、前の表を使い回す。呼ぶ側が開いている元DB の接続を受け取る。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, forecast: PaceForecast, slopes: pd.DataFrame, table: PriorSlopeTable) -> None:
        self._con = con
        self._source = RaceBiasSource(forecast, slopes, table)
        self._attachment = BiasAttachment()
        self._last: tuple[tuple[str, PredictionTiming], pd.DataFrame] | None = None

    def attach(self, data: PredictionData, race_id: str, timing: PredictionTiming, given: OddsInput | None) -> PredictionData:
        key = (race_id, timing)
        if self._last is None or self._last[0] != key:
            self._last = (key, self._source.of(self._con, race_id, timing, given))
        return self._attachment.apply(data, self._last[1])
