"""CatBoost で学習・予測する。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import catboost
import numpy as np
import pandas as pd

from ..dataset import TrainingData
from ..setting import CatBoostSettings, HyperparameterSettings
from .catboost_encoder import CatBoostEncoder
from .probability_model import FeatureData


class CatBoostModel:
    """CatBoost で学習・予測する（設計書 13）。``ProbabilityModel`` を守る。

    多クラス分類（``CatBoostMulticlassModel``）は、このクラスの目的関数・目的変数の渡し方・確率の取り出し方だけを
    変えたもの。学習・保存・読み込みの手順は同じである。
    """

    name = "CatBoost"
    file_name = "catboost.cbm"
    #: 目的関数。二値分類。設定ファイルでは変えられない（設計書 14）。
    loss_function = "Logloss"

    def __init__(self, settings: CatBoostSettings) -> None:
        self._settings = settings
        self._encoder: CatBoostEncoder | None = None
        self._classifier: catboost.CatBoostClassifier | None = None

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(settings.catboost)

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習する。検証データの当たり具合が、木を足しても良くならなくなったら止める（設計書 13 の 4）。"""
        self._check_labels(train)
        encoder = CatBoostEncoder(train.features.columns, train.categorical_columns)
        # verbose=0 は途中経過を表示しない、allow_writing_files=False は作業用のフォルダを作らない
        classifier = catboost.CatBoostClassifier(
            loss_function=self.loss_function, verbose=0, allow_writing_files=False,
            **self._settings.params,
        )
        classifier.fit(
            encoder.transform(train.features), self._label(train),
            cat_features=list(encoder.categorical_columns),
            eval_set=(encoder.transform(valid.features), self._label(valid)),
            early_stopping_rounds=self._settings.early_stopping_rounds,
        )
        self._encoder, self._classifier = encoder, classifier
        return self

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの、目的変数が 1 になる確率（設計書 13 の 5）。"""
        encoder, classifier = self._trained()
        return self._probabilities(classifier.predict_proba(encoder.transform(data.features)))

    @property
    def tree_count(self) -> int:
        _, classifier = self._trained()
        return int(classifier.tree_count_)

    def save(self, path: Path) -> None:
        """学習済みの ``CatBoostClassifier`` を書く。列名とカテゴリ特徴量の列名は、モデルの中に残る（設計書 13 の 6）。"""
        _, classifier = self._trained()
        classifier.save_model(str(path))

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        classifier = catboost.CatBoostClassifier()
        classifier.load_model(str(path))
        columns = list(classifier.feature_names_)
        categorical_columns = [columns[index] for index in classifier.get_cat_feature_indices()]
        model = cls(settings.catboost)
        model._encoder = CatBoostEncoder(columns, categorical_columns)
        model._classifier = classifier
        return model

    def _check_labels(self, train: TrainingData) -> None:
        """学習の前に目的変数を確かめる。二値分類では何もしない。"""

    def _label(self, data: TrainingData) -> pd.Series:
        """ライブラリの ``fit`` に渡す目的変数。"""
        return data.label

    def _probabilities(self, matrix: np.ndarray) -> np.ndarray:
        """ライブラリの ``predict_proba`` の戻り値から、返す確率を取り出す。二値分類は2列目。"""
        return matrix[:, 1]

    def _trained(self) -> tuple[CatBoostEncoder, catboost.CatBoostClassifier]:
        if self._encoder is None or self._classifier is None:
            raise RuntimeError("CatBoost のモデルがまだ学習していません（fit か load を先に呼んでください）")
        return self._encoder, self._classifier
