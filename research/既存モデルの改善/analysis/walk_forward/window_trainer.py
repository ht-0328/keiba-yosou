"""1つの区切り・1つの作り方で学習し、検証とテストの予測を返す。"""

from __future__ import annotations

import time
from collections.abc import Sequence
from itertools import chain

import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import MEMBER_TYPES, ProbabilityModel
from yosou.shared.setting import HyperparameterSettings

from ..variants import ModelVariant
from ..windows import TestWindow
from .prediction_frame import PART_TEST, PART_VALID, PredictionFrame


class WindowTrainer:
    """1つの区切り・1つの作り方で、LightGBM と CatBoost を学習し、検証期間とテスト期間の予測を返す。

    学習データを分ける作り方（穴馬の区分・人気帯）は、区分ごとに別のモデルを学ぶ。
    学習の記録（区分・モデル・木の数・学習の行数・秒）も返す。
    """

    def __init__(self, settings: HyperparameterSettings,
                 member_types: Sequence[type[ProbabilityModel]] = MEMBER_TYPES) -> None:
        self._settings = settings
        self._member_types = tuple(member_types)
        self._frame = PredictionFrame()

    def run(self, data: TrainingData, window: TestWindow,
            variant: ModelVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        """（予測の表, 学習の記録の行）。"""
        prepared = variant.prepare(data)
        train, valid, test = window.train(prepared), window.valid(prepared), window.test(prepared)
        results = [self._segment(train, valid, test, window, variant, segment) for segment in variant.segments(train)]
        frames = [frame for frame, _ in results]
        logs = list(chain.from_iterable(rows for _, rows in results))
        return pd.concat(frames, ignore_index=True), logs

    def _segment(self, train: TrainingData, valid: TrainingData, test: TrainingData, window: TestWindow,
                 variant: ModelVariant, segment: str) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        """1つの区分を学習して、検証とテストの予測を作る。"""
        parts = {name: data.where(variant.rows_of(data, segment)) for name, data in
                 (("train", train), ("valid", valid), ("test", test))}
        started = time.perf_counter()
        members = [member_type.from_settings(self._settings).fit(parts["train"], parts["valid"])
                   for member_type in self._member_types]
        seconds = round(time.perf_counter() - started, 1)
        frames = [self._predict(members, parts[key], window, part, segment)
                  for key, part in (("valid", PART_VALID), ("test", PART_TEST))]
        logs = [self._log_row(window, variant, segment, member, len(parts["train"]), seconds) for member in members]
        return pd.concat(frames, ignore_index=True), logs

    def _predict(self, members: list[ProbabilityModel], data: TrainingData, window: TestWindow,
                 part: str, segment: str) -> pd.DataFrame:
        probabilities = {member.name: member.predict_proba(data) for member in members}
        return self._frame.build(data, probabilities, window.name, part, segment)

    def _log_row(self, window: TestWindow, variant: ModelVariant, segment: str, member: ProbabilityModel,
                 rows: int, seconds: float) -> dict[str, object]:
        return {
            "区切り": window.name, "作り方": variant.name, "区分": segment, "モデル": member.name,
            "木の数": member.tree_count, "学習の行数": rows, "2つのモデルの学習の秒": seconds,
        }
