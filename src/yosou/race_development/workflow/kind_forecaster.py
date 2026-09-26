"""1つの予想の2つのモデルで予測し、予測の列の表にする。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import numpy as np
import pandas as pd

from yosou.shared.ml_model import EnsembleModel, FeatureData

from ..ml_model import QuantileEnsemble, RegressionEnsemble
from .development_model_kind import DevelopmentModelKind
from .model_family import ModelFamily


class KindForecaster:
    """1つの予想の LightGBM と CatBoost の予測を平均して、その予想の予測の列（``KindSpec.outputs``）の表にする。

    二値（レースの中でそろえる）と多クラスは確率の平均、分位点回帰は分位点の平均を並べ直したもの、回帰は値の平均。
    """

    def __init__(self) -> None:
        self._predictors: dict[ModelFamily, Callable[[Sequence[Any], FeatureData], np.ndarray]] = {
            ModelFamily.WITHIN_RACE: lambda members, data: EnsembleModel(members).predict_proba(data),
            ModelFamily.MULTICLASS: lambda members, data: EnsembleModel(members).predict_proba(data),
            ModelFamily.QUANTILE: lambda members, data: QuantileEnsemble(members).predict_quantiles(data),
            ModelFamily.REGRESSION: lambda members, data: RegressionEnsemble(members).predict(data),
        }

    def predict(self, kind: DevelopmentModelKind, members: Sequence[Any], data: FeatureData) -> pd.DataFrame:
        """列は ``kind.spec.outputs``、行の並びと index は ``data.features`` と同じ。"""
        values = self._predictors[kind.spec.family](members, data)
        matrix = np.asarray(values, dtype="float64").reshape(len(data), len(kind.spec.outputs))
        return pd.DataFrame(matrix, columns=list(kind.spec.outputs), index=data.features.index)
