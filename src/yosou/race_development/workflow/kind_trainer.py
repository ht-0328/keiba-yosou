"""1つの予想の、LightGBM と CatBoost のモデルを学習する。"""

from __future__ import annotations

from typing import Any

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import CLASS_MEMBER_TYPES
from yosou.shared.setting import HyperparameterSettings

from ..ml_model import (
    CatBoostQuantileModel,
    CatBoostRegressionModel,
    CatBoostWithinRaceModel,
    LightGbmQuantileModel,
    LightGbmRegressionModel,
    LightGbmWithinRaceModel,
)
from .development_model_kind import DevelopmentModelKind
from .model_family import ModelFamily

#: モデルの種類ごとの、学習するクラスの並び（LightGBM と CatBoost。設計書 12・13 の 2）。
MEMBER_TYPES: dict[ModelFamily, tuple[Any, ...]] = {
    ModelFamily.WITHIN_RACE: (LightGbmWithinRaceModel, CatBoostWithinRaceModel),
    ModelFamily.MULTICLASS: CLASS_MEMBER_TYPES,
    ModelFamily.QUANTILE: (LightGbmQuantileModel, CatBoostQuantileModel),
    ModelFamily.REGRESSION: (LightGbmRegressionModel, CatBoostRegressionModel),
}


class KindTrainer:
    """1つの予想について、LightGBM と CatBoost のモデルを1つずつ学習する。

    学習データと検証データは、その時点で使う列だけにし、目的変数を持ち替えたものを渡す。
    """

    def fit(self, kind: DevelopmentModelKind, train: TrainingData, valid: TrainingData,
            settings: HyperparameterSettings) -> list[Any]:
        """学習した2つのモデル（LightGBM・CatBoost の順）。"""
        return [model_type.from_settings(settings).fit(train, valid) for model_type in MEMBER_TYPES[kind.spec.family]]
