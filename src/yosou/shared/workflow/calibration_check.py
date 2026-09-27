"""確率のずれを確かめる材料の表を作る。"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import product

import numpy as np
import pandas as pd

from ..dataset import SplitData, TrainingData
from ..dataset.column_names import PLACE_PAYOUT, POPULARITY
from ..feature import PredictionTiming
from ..place_value import PLACE_PROBABILITY, PLACE_VALUE, PlaceExpectedValue
from .model_segments import ModelSegments
from .segmented_holdout_prediction import SegmentedHoldoutPrediction

#: 材料の表の列の名前（``POPULARITY``・``PLACE_PAYOUT``・``PLACE_PROBABILITY``・``PLACE_VALUE`` はそのままの名前で入る）。
TIMING, PART, SEGMENT, LABEL, PROBABILITY = "時点", "期間", "区分", "正解", "確率"
#: 期間の名前（学習の報告の「検証」「テスト」と同じ）。
PART_VALID, PART_TEST = "検証", "テスト"


class CalibrationCheck:
    """保存したモデルで、学習に使っていない期間（検証・テスト）の馬を時点ごとに予測し、確率のずれを測る材料の表を作る
    （穴馬の設計書 16 の 4）。流れを進めるだけで、ずれの計算は ``ProbabilityBands``・``ValueBands`` が行う。

    表は 1行 = 1頭 × 1時点。列は 時点・期間・区分・正解（目的変数）・確率（2つのモデルの平均）・確定単勝人気・複勝の払戻と、
    オッズが分かる時点（前日・当日）なら複勝的中の確率と複勝の期待値。木曜は、予測と同じく期待値を出さない（欠損値）。
    ``place_value`` が None（見込みの倍率を保存していない）なら、どの時点も期待値を出さない。
    """

    def __init__(self, segments: ModelSegments, predictor: SegmentedHoldoutPrediction,
                 place_value: PlaceExpectedValue | None, timings: Sequence[PredictionTiming]) -> None:
        self._segments = segments
        self._predictor = predictor
        self._place_value = place_value
        self._timings = tuple(timings)

    def run(self, split: SplitData) -> pd.DataFrame:
        parts = {PART_VALID: split.valid, PART_TEST: split.test}
        frames = [self._one(name, data, timing) for (name, data), timing in product(parts.items(), self._timings)]
        return pd.concat(frames, ignore_index=True)

    def _one(self, part: str, data: TrainingData, timing: PredictionTiming) -> pd.DataFrame:
        probability = self._predictor.predict(data, timing)
        frame = pd.DataFrame({
            TIMING: timing.label, PART: part, SEGMENT: self._segments.labels_of(data.evaluation),
            LABEL: data.label, PROBABILITY: probability,
            POPULARITY: data.evaluation[POPULARITY], PLACE_PAYOUT: data.evaluation[PLACE_PAYOUT],
        }, index=data.ids.index)
        joined = pd.concat([frame, self._values(probability, data, timing)], axis=1)
        return joined.sort_values(SEGMENT, key=self._segment_order, kind="stable")

    def _segment_order(self, labels: pd.Series) -> pd.Series:
        """区分の並び（中穴 → 大穴 のように、``ModelSegments`` に書いた順）。表をその順に並べるために使う。"""
        order = {label: position for position, label in enumerate(self._segments.labels())}
        return labels.map(order)

    def _values(self, probability: pd.Series, data: TrainingData, timing: PredictionTiming) -> pd.DataFrame:
        """複勝的中の確率と複勝の期待値。オッズの分からない時点（基準の無い時点）は欠損値（予測の ``PlaceValueColumns`` と同じ）。"""
        if self._place_value is None or data.for_timing(timing).baseline is None:
            return pd.DataFrame({PLACE_PROBABILITY: np.nan, PLACE_VALUE: np.nan}, index=data.ids.index)
        return self._place_value.of(probability, data.evaluation)[[PLACE_PROBABILITY, PLACE_VALUE]]
