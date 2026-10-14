"""テスト期間の特別競走の行だけで、予測の当たり具合を測る。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TOP3, TrainingData
from yosou.shared.dataset.column_names import FIELD_SIZE
from yosou.shared.evaluation import ENSEMBLE_NAME, Evaluation, ModelEvaluator
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES
from yosou.shared.workflow import FIELD_SHARE_NAME
from yosou.shared.workflow.backtest_workflow import PREDICTION_COLUMNS

from ..feature import SPECIAL_RACE
from .special_race_rows import SpecialRaceRows

#: 予測の表の列（レースID・馬ID・平均の確率・区切り）。
_RACE, _HORSE, _PROBABILITY, WINDOW = PREDICTION_COLUMNS[0], PREDICTION_COLUMNS[2], PREDICTION_COLUMNS[4], PREDICTION_COLUMNS[5]
#: 確率を 0・1 に張り付かせない幅。
_EPSILON = 1e-6
#: 目的変数ごとの、3着以内（1着）に入る頭数。
_PLACES: dict[str, int] = {TOP3: 3}


class SpecialRaceEvaluation:
    """テスト期間の行（``TrainingData``）のうち特別競走の行（Y = 1）だけで、``BacktestWorkflow`` が書いた予測の表の確率の当たり具合を測る
    （設計書 16 の 4）。モデルごと・平均の行と、頭数から見た割合（3 ÷ 頭数、1 ÷ 頭数。採用の基準）の行を出す。"""

    def __init__(self) -> None:
        self._evaluator = ModelEvaluator()

    def rows_of(self, test: TrainingData, predictions: pd.DataFrame, window: str) -> SpecialRaceRows:
        """``test`` の特別競走の行と、予測の表（レースID・馬ID で突き合わせる）の確率。評価用の列に区切りの名前（``window``）を足す。"""
        special = test.where(test.features[SPECIAL_RACE].eq(1.0))
        special = replace(special, evaluation=special.evaluation.assign(**{WINDOW: window}))
        keys = pd.DataFrame({_RACE: special.ids[RACE_ID].astype(str).to_numpy(), _HORSE: special.ids[HORSE_ID].astype(str).to_numpy()})
        names = [model_type.name for model_type in MEMBER_TYPES]
        table = predictions.assign(**{_RACE: predictions[_RACE].astype(str), _HORSE: predictions[_HORSE].astype(str)})
        aligned = keys.merge(table.drop_duplicates([_RACE, _HORSE])[[_RACE, _HORSE, _PROBABILITY, *names]], on=[_RACE, _HORSE], how="left")
        probabilities = {**{name: aligned[name].to_numpy(dtype=float) for name in names},
                         ENSEMBLE_NAME: aligned[_PROBABILITY].to_numpy(dtype=float)}
        return SpecialRaceRows(special, probabilities)

    def evaluate(self, timing: PredictionTiming, rows: SpecialRaceRows) -> list[Evaluation]:
        """モデルごと・平均の行と、頭数から見た割合の行。"""
        timed = rows.data.for_timing(timing)
        evaluations = self._evaluator.evaluate_probabilities(timing, timed, rows.probabilities)
        places = _PLACES.get(rows.data.label_name, 1)
        share = places / pd.to_numeric(timed.evaluation[FIELD_SIZE], errors="coerce")
        clipped = share.fillna(0.5).clip(_EPSILON, 1 - _EPSILON).to_numpy()
        return evaluations + self._evaluator.evaluate_probabilities(timing, timed, {FIELD_SHARE_NAME: clipped})
