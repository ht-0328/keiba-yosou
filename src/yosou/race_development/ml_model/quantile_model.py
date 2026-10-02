"""分位点回帰のモデルに共通の決まり。"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Protocol, Self

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings


class QuantileModel(Protocol):
    """10%・50%・90% の分位点を当てるモデル（③ 前半タイム・⑥ 後半タイム。設計書 03 の 3）。"""

    name: ClassVar[str]
    file_name: ClassVar[str]

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        ...

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        ...

    def predict_quantiles(self, data: FeatureData) -> np.ndarray:
        """行数 × 3（10%・50%・90% の値）。"""
        ...

    @property
    def tree_count(self) -> int:
        ...

    def save(self, path: Path) -> None:
        ...

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        ...
