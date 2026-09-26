"""回帰のモデルに共通の決まり。"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Protocol, Self

import numpy as np

from yosou.shared.dataset import TrainingData
from yosou.shared.ml_model import FeatureData
from yosou.shared.setting import HyperparameterSettings


class RegressionModel(Protocol):
    """値そのものを当てるモデル（④ 4コーナーの位置・⑤ 上がりの速さ。設計書 03 の 4）。

    確率ではなく値を返すので、``predict_proba`` ではなく ``predict`` を持つ（名前と中身が食い違わないように。設計書 04 の 1）。
    """

    name: ClassVar[str]
    file_name: ClassVar[str]

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        ...

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習データで学習する。木の数は、検証データで早期終了して決める。"""
        ...

    def predict(self, data: FeatureData) -> np.ndarray:
        """1行ずつの値（長さは行数）。"""
        ...

    @property
    def tree_count(self) -> int:
        ...

    def save(self, path: Path) -> None:
        ...

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        ...
