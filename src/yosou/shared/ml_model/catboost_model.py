"""CatBoost で学習・予測する。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import catboost
import numpy as np

from ..dataset import TrainingData
from ..setting import CatBoostSettings, HyperparameterSettings
from .catboost_encoder import CatBoostEncoder
from .probability_model import FeatureData

#: 目的関数。二値分類。設定ファイルでは変えられない（設計書 14）。
_LOSS_FUNCTION = "Logloss"


class CatBoostModel:
    """CatBoost で学習・予測する（設計書 13）。``ProbabilityModel`` を守る。"""

    name = "CatBoost"
    file_name = "catboost.cbm"

    def __init__(self, settings: CatBoostSettings) -> None:
        self._settings = settings
        self._encoder: CatBoostEncoder | None = None
        self._classifier: catboost.CatBoostClassifier | None = None

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(settings.catboost)

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習する。検証データの当たり具合が、木を足しても良くならなくなったら止める（設計書 13 の 4）。"""
        encoder = CatBoostEncoder(train.features.columns, train.categorical_columns)
        # verbose=0 は途中経過を表示しない、allow_writing_files=False は作業用のフォルダを作らない
        classifier = catboost.CatBoostClassifier(
            loss_function=_LOSS_FUNCTION, verbose=0, allow_writing_files=False,
            **self._settings.params,
        )
        classifier.fit(
            encoder.transform(train.features), train.label,
            cat_features=list(encoder.categorical_columns),
            eval_set=(encoder.transform(valid.features), valid.label),
            early_stopping_rounds=self._settings.early_stopping_rounds,
        )
        self._encoder, self._classifier = encoder, classifier
        return self

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの、目的変数が 1 になる確率（設計書 13 の 5）。"""
        encoder, classifier = self._trained()
        return classifier.predict_proba(encoder.transform(data.features))[:, 1]

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

    def _trained(self) -> tuple[CatBoostEncoder, catboost.CatBoostClassifier]:
        if self._encoder is None or self._classifier is None:
            raise RuntimeError("CatBoost のモデルがまだ学習していません（fit か load を先に呼んでください）")
        return self._encoder, self._classifier
