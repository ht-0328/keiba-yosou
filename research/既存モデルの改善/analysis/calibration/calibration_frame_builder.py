"""区切りごとの予測から、確率のずれを測る材料の表を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_DATE, TrainingData
from yosou.shared.dataset.column_names import PLACE_ODDS_LOW, PLACE_PAYOUT, POPULARITY
from yosou.shared.feature import PredictionTiming
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE, PlaceExpectedValue, PlacePriceEstimator
from yosou.shared.workflow.calibration_check import LABEL, PART, PROBABILITY, SEGMENT, TIMING

from ..comparison.prediction_join import LABEL as JOINED_LABEL
from ..comparison.prediction_join import PredictionJoin
from ..walk_forward import PREDICTION_COLUMN, WINDOW
from ..walk_forward import SEGMENT as PREDICTED_SEGMENT
from ..windows import TestWindow

#: 材料の表に足す、区切りの名前の列（``WINDOW`` と同じ名前）。
WINDOW_COLUMN = WINDOW


class CalibrationFrameBuilder:
    """区切りごとの予測（``walk_forward.py`` の出力）を、本番の ``CalibrationCheck`` と同じ列の材料の表にする。

    列は 時点・期間（検証・テスト）・区分・正解・確率・確定単勝人気・複勝の払戻・複勝的中の確率・複勝の期待値・区切り。
    複勝の見込みの倍率は、本番の学習と同じく、区切りごとに検証期間より前（学習期間）の払戻で決める。
    オッズの分からない時点（木曜）は、本番の予測と同じく期待値を出さない（欠損値）。
    """

    def __init__(self, data: TrainingData, windows: tuple[TestWindow, ...]) -> None:
        self._join = PredictionJoin(data)
        self._history = pd.concat([data.ids, data.evaluation], axis=1)
        self._windows = windows

    def build(self, predictions: pd.DataFrame, timing: PredictionTiming) -> pd.DataFrame:
        joined = self._join.of(predictions)
        parts = [self._window(joined[joined[WINDOW] == window.name], window, timing) for window in self._windows]
        return pd.concat(parts, ignore_index=True)

    def _window(self, joined: pd.DataFrame, window: TestWindow, timing: PredictionTiming) -> pd.DataFrame:
        frame = pd.DataFrame({
            TIMING: timing.label, PART: joined[PART], SEGMENT: joined[PREDICTED_SEGMENT].astype(str),
            LABEL: joined[JOINED_LABEL], PROBABILITY: joined[PREDICTION_COLUMN], POPULARITY: joined[POPULARITY],
            PLACE_PAYOUT: joined[PLACE_PAYOUT], WINDOW_COLUMN: window.name,
        }, index=joined.index)
        return pd.concat([frame, self._values(joined, window, timing)], axis=1)

    def _values(self, joined: pd.DataFrame, window: TestWindow, timing: PredictionTiming) -> pd.DataFrame:
        """複勝的中の確率と期待値。木曜（オッズから作った基準の無い時点）は欠損値。"""
        if not timing.is_at_or_after(PredictionTiming.DAY_BEFORE):
            return pd.DataFrame({PLACE_PROBABILITY: np.nan, PLACE_VALUE: np.nan}, index=joined.index)
        values = PlaceExpectedValue(self._estimator(window)).of(joined[PREDICTION_COLUMN], joined)
        return values[[PLACE_PROBABILITY, PLACE_VALUE]]

    def _estimator(self, window: TestWindow) -> PlacePriceEstimator:
        before = self._history[self._history[RACE_DATE] < pd.Timestamp(window.valid_first_day)]
        return PlacePriceEstimator().fit(before[PLACE_ODDS_LOW], before[PLACE_PAYOUT].fillna(0.0))
