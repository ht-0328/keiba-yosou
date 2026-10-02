"""CatBoost で学習・予測する。"""

from __future__ import annotations

from pathlib import Path
from typing import Self

import catboost
import numpy as np
import pandas as pd

from ..dataset import TrainingData
from ..setting import CatBoostSettings, HyperparameterSettings
from .baseline_check import BaselineCheck
from .catboost_encoder import CatBoostEncoder
from .probability_model import FeatureData

#: 基準を使って学んだかを、モデルのメタデータに書くときの名前と値。
_USES_BASELINE_KEY = "uses_baseline"
_YES = "1"


class CatBoostModel:
    """CatBoost で学習・予測する（設計書 13）。``ProbabilityModel`` を守る。

    多クラス分類（``CatBoostMulticlassModel``）は、このクラスの目的関数・目的変数の渡し方・確率の取り出し方だけを
    変えたもの。学習・保存・読み込みの手順は同じである。

    学習データに目的変数の基準（``TrainingData.baseline``）があれば、それを出発点（``Pool`` の ``baseline``）にして、
    基準からの上げ下げだけを学ぶ（既存モデルの修正計画の 1・2）。予測では、木の出した値に基準を足して確率に戻す。
    基準を使って学んだかどうかは、モデルのメタデータに書いて一緒に保存する。
    """

    name = "CatBoost"
    file_name = "catboost.cbm"
    #: 目的関数。二値分類。設定ファイルでは変えられない（設計書 14）。
    loss_function = "Logloss"

    def __init__(self, settings: CatBoostSettings) -> None:
        self._settings = settings
        self._encoder: CatBoostEncoder | None = None
        self._classifier: catboost.CatBoostClassifier | None = None
        self._baseline_check = BaselineCheck(uses_baseline=False)

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
            self._pool(encoder, train), eval_set=self._pool(encoder, valid),
            early_stopping_rounds=self._settings.early_stopping_rounds,
        )
        uses_baseline = train.baseline is not None
        classifier.get_metadata()[_USES_BASELINE_KEY] = _YES if uses_baseline else ""
        self._encoder, self._classifier = encoder, classifier
        self._baseline_check = BaselineCheck(uses_baseline=uses_baseline)
        return self

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの、目的変数が 1 になる確率（設計書 13 の 5）。基準を使って学んだモデルは、基準を足して確率に戻す。"""
        encoder, classifier = self._trained()
        pool = catboost.Pool(encoder.transform(data.features), cat_features=list(encoder.categorical_columns))
        if not self._baseline_check.uses_baseline:
            return self._probabilities(classifier.predict_proba(pool))
        raw = classifier.predict(pool, prediction_type="RawFormulaVal") + self._baseline_check.values_of(data)
        return 1.0 / (1.0 + np.exp(-raw))

    @property
    def tree_count(self) -> int:
        _, classifier = self._trained()
        return int(classifier.tree_count_)

    def save(self, path: Path) -> None:
        """学習済みの ``CatBoostClassifier`` を書く。列名・カテゴリ特徴量の列名・基準を使ったかは、モデルの中に残る（設計書 13 の 6）。"""
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
        uses_baseline = dict(classifier.get_metadata()).get(_USES_BASELINE_KEY, "") == _YES
        model._baseline_check = BaselineCheck(uses_baseline=uses_baseline)
        return model

    def _pool(self, encoder: CatBoostEncoder, data: TrainingData) -> catboost.Pool:
        """ライブラリに渡すデータ。基準があれば、出発点（``baseline``）として付ける。"""
        baseline = data.baseline.array() if data.baseline is not None else None
        return catboost.Pool(
            encoder.transform(data.features), self._label(data),
            cat_features=list(encoder.categorical_columns), baseline=baseline,
        )

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
