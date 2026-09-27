"""既存の予想の、1つのモデル（区分・券種ごと）の決めごとと、学習・予測。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from yosou.shared.dataset import PredictionData, TrainingData
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.setting import HyperparameterSettings
from yosou.shared.workflow import WHOLE, ModelSegments

from .tendency_output import TendencyOutput


@dataclass(frozen=True)
class TendencyUnit:
    """既存の予想が別々に学ぶ1つのモデル（例: 人気馬の「1番人気」の区分、荒れ具合の「単勝」）。

    - ``folder``: モデルを置くフォルダの名前（``<置き場所>/tendency/<既存の予想>/<folder>/<時点>/``）。
    - ``segments``・``segment``: 既存の予想の区分の分け方と、この単位の区分の名前（分けない予想は「全体」）。
    - ``label``: 目的変数の列（None なら、既存の予想の学習データの目的変数のまま）。
    - ``member_types``: 学習するモデルのクラス（LightGBM と CatBoost。二値分類か多クラス分類か）。
    - ``output``: 確率を、傾向の組の予測の列にする決まり。

    既存の予想と同じ学習データ・特徴量・目的変数・基準（オッズから見た確率）・区分で学び、期間だけを年ごとに変える。
    """

    folder: str
    member_types: Sequence[Any]
    output: TendencyOutput
    segments: ModelSegments = ModelSegments()
    segment: str = WHOLE
    label: str | None = None

    def samples(self, data: TrainingData) -> TrainingData:
        """この単位の区分の行で、目的変数のある行。"""
        chosen = data.where(self.segments.rows(data.evaluation, self.segment))
        return chosen.with_label(self.label or chosen.label_name)

    def targets(self, data: TrainingData) -> TrainingData:
        """この単位の区分の行（予測するサンプル。目的変数が無くてもよい）。"""
        return data.where(self.segments.rows(data.evaluation, self.segment))

    def runners(self, data: PredictionData) -> PredictionData:
        """予測用データのうち、この単位の区分の行。"""
        return data.where(self.segments.rows(data.ids, self.segment))

    def fit(self, train: TrainingData, valid: TrainingData, settings: HyperparameterSettings) -> list[Any]:
        """学習した2つのモデル（LightGBM・CatBoost の順）。"""
        return [model_type.from_settings(settings).fit(train, valid) for model_type in self.member_types]

    def predict(self, members: Sequence[Any], data: TrainingData | PredictionData) -> pd.DataFrame:
        """列は ``output.columns``、行の並びと index は ``data.features`` と同じ。"""
        probabilities = EnsembleModel(members).predict_proba(data)
        return pd.DataFrame(self.output.of(probabilities), index=data.features.index)
