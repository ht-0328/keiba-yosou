"""2つのモデル（LightGBM・CatBoost）に共通の決まり。"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Protocol, Self

import numpy as np

from ..dataset import PredictionData, TrainingData
from ..setting import HyperparameterSettings

#: 予測確率を出せるデータ（学習データか予測用データ）。どちらも ``features`` を持つ。
FeatureData = TrainingData | PredictionData


class ProbabilityModel(Protocol):
    """3着以内に入る確率を出すモデル（設計書 04）。

    この決まりを守るクラスなら、呼ぶ側は LightGBM か CatBoost かを区別せずに扱える。
    モデルごとの違い（カテゴリ特徴量の渡し方など）は、それぞれのクラスとエンコーダーの中に閉じる。
    """

    #: 表に出す名前（例: LightGBM）。
    name: ClassVar[str]
    #: 保存するファイルの名前（例: lightgbm.joblib）。
    file_name: ClassVar[str]

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        """設定から、まだ学習していないモデルを作る。"""
        ...

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習データで学習する。木の数は、検証データで早期終了して決める。学習したモデル自身を返す。"""
        ...

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの「3着以内に入る確率」（ライブラリの ``predict_proba`` の2列目）。"""
        ...

    @property
    def tree_count(self) -> int:
        """学習で作った（早期終了で残った）木の数。"""
        ...

    def save(self, path: Path) -> None:
        """学習したモデルをファイルに書く。"""
        ...

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        """``save`` で書いたファイルから読む。``settings`` は学習に使った設定。"""
        ...
