"""第1段: レースが帯になる確率を、1つの区切りで学ぶ。"""

from __future__ import annotations

import time

import pandas as pd

from yosou.shared.dataset import BINARY_LABELS, TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES, ProbabilityModel
from yosou.shared.setting import HyperparameterSettings

from 既存モデルの改善.analysis.variants.model_variant import WHOLE
from 既存モデルの改善.analysis.walk_forward.prediction_frame import PART_TEST, PART_VALID, PredictionFrame
from 既存モデルの改善.analysis.windows import TestWindow

from .race_table_loader import OBI_LABEL


class RaceObiWindowTrainer:
    """レース単位の表（1行 = 1レース）で、目的変数「帯」（二値）を LightGBM と CatBoost で学び、検証とテストの予測を返す。

    特徴量は、その時点（既定は当日）で使える列。オッズから作った基準は使わない（レース単位の表には無い）。
    予測の表は、ほかの予想と同じ形（区切り・期間・区分・レースID・開催日・モデルごとの確率・その平均）。
    """

    def __init__(self, settings: HyperparameterSettings, timing: PredictionTiming = PredictionTiming.RACE_DAY,
                 label: str = OBI_LABEL) -> None:
        self._settings = settings
        self._timing = timing
        self._label = label
        self._frame = PredictionFrame()

    def run(self, data: TrainingData, window: TestWindow) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        """（予測の表, 学習の記録の行）。"""
        labeled = data.for_timing(self._timing).with_label(self._label, BINARY_LABELS)
        train, valid, test = window.train(labeled), window.valid(labeled), window.test(labeled)
        started = time.perf_counter()
        members = [member_type.from_settings(self._settings).fit(train, valid) for member_type in MEMBER_TYPES]
        seconds = round(time.perf_counter() - started, 1)
        frames = [self._predict(members, part, window, name) for part, name in ((valid, PART_VALID), (test, PART_TEST))]
        logs = [{"区切り": window.name, "目的変数": self._label, "モデル": member.name, "木の数": member.tree_count,
                 "学習の行数": len(train), "学習の帯の数": int(train.label.sum()), "2つのモデルの学習の秒": seconds}
                for member in members]
        return pd.concat(frames, ignore_index=True), logs

    def _predict(self, members: list[ProbabilityModel], data: TrainingData, window: TestWindow, part: str) -> pd.DataFrame:
        probabilities = {member.name: member.predict_proba(data) for member in members}
        return self._frame.build(data, probabilities, window.name, part, WHOLE)
