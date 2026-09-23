"""多クラス分類の2つのモデル（LightGBM・CatBoost）に共通の決まり。"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Protocol, Self

import numpy as np

from ..dataset import TrainingData
from ..setting import HyperparameterSettings
from .probability_model import FeatureData


class ClassProbabilityModel(Protocol):
    """クラスごとの確率を出すモデル（荒れ具合の設計書 04 の 2）。荒れ具合の予想では「固い・中荒れ・大荒れ・超荒れ」の4つ。

    ``ProbabilityModel`` と同じ名前のメソッドを持ち、違うのは ``predict_proba`` の戻り値の形（行数 × クラスの数）だけ。
    ``EnsembleModel`` は、どちらの決まりのモデルでも同じ形で平均する。
    """

    #: 表に出す名前（例: LightGBM）。
    name: ClassVar[str]
    #: 保存するファイルの名前（例: lightgbm.joblib）。
    file_name: ClassVar[str]

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        """設定から、まだ学習していないモデルを作る。クラスの数は学習データから決める。"""
        ...

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習データで学習する。木の数は、検証データで早期終了して決める。学習したモデル自身を返す。"""
        ...

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1行ずつの、クラスごとの確率（行数 × クラスの数。各行の合計は 1。列の順はクラスの番号の順）。"""
        ...

    @property
    def tree_count(self) -> int:
        """学習で作った（早期終了で残った）木の数（LightGBM は反復の回数）。"""
        ...

    def save(self, path: Path) -> None:
        """学習したモデルをファイルに書く。"""
        ...

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        """``save`` で書いたファイルから読む。``settings`` は学習に使った設定。"""
        ...
