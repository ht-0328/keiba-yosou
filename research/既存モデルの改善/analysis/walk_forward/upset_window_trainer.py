"""荒れ具合の予想（現行の作り方）を、1つの区切りで券種ごとに学習し、検証とテストの予測を返す。"""

from __future__ import annotations

import time
from itertools import chain

import numpy as np
import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID, TrainingData
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import CLASS_MEMBER_TYPES, EnsembleModel
from yosou.shared.setting import HyperparameterSettings
from yosou.upset_level.dataset import BetType, UpsetLevel

from ..windows import TestWindow
from .prediction_frame import PART, PART_TEST, PART_VALID, WINDOW

#: 予測の表の、券種の列の名前。
BET = "券種"


class UpsetWindowTrainer:
    """荒れ具合の予想の現行の作り方（券種ごと・4クラス・LightGBM と CatBoost の平均）を、1つの区切りで学習する。

    学習データ（1行 = 1レース）は、予想のパッケージの ``race_dataset_builder`` で作った表。券種ごとに目的変数の列を
    持ち替えて学び（``TrainingData.with_label``）、検証とテストの予測（固い〜超荒れの4つの確率）を返す。
    """

    def __init__(self, settings: HyperparameterSettings, timing: PredictionTiming = PredictionTiming.RACE_DAY) -> None:
        self._settings = settings
        self._timing = timing

    def run(self, data: TrainingData, window: TestWindow) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        """（予測の表, 学習の記録の行）。"""
        timed = data.for_timing(self._timing)
        results = [self._bet(timed, window, bet) for bet in BetType]
        frames = [frame for frame, _ in results]
        return pd.concat(frames, ignore_index=True), list(chain.from_iterable(rows for _, rows in results))

    def _bet(self, data: TrainingData, window: TestWindow, bet: BetType) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        labeled = data.with_label(bet.column_name)
        train, valid, test = window.train(labeled), window.valid(labeled), window.test(labeled)
        started = time.perf_counter()
        members = [member_type.from_settings(self._settings).fit(train, valid) for member_type in CLASS_MEMBER_TYPES]
        seconds = round(time.perf_counter() - started, 1)
        ensemble = EnsembleModel(members)
        frames = [self._frame(ensemble, part_data, window, part, bet)
                  for part_data, part in ((valid, PART_VALID), (test, PART_TEST))]
        logs = [{"区切り": window.name, "券種": bet.label, "モデル": member.name, "木の数": member.tree_count,
                 "学習の行数": len(train), "2つのモデルの学習の秒": seconds} for member in members]
        return pd.concat(frames, ignore_index=True), logs

    def _frame(self, ensemble: EnsembleModel, data: TrainingData, window: TestWindow, part: str,
               bet: BetType) -> pd.DataFrame:
        probabilities = np.asarray(ensemble.predict_proba(data))
        by_level = {level.label: probabilities[:, level.value] for level in UpsetLevel}
        ids = data.ids[[RACE_ID, RACE_DATE]]
        return ids.assign(**by_level, **{WINDOW: window.name, PART: part, BET: bet.label})
