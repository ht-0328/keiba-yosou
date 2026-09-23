"""LightGBM で学習・予測する。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import joblib
import lightgbm
import numpy as np
import pandas as pd

from ..dataset import TrainingData
from ..setting import HyperparameterSettings, LightGbmSettings
from .baseline_check import BaselineCheck
from .lightgbm_encoder import LightGbmEncoder
from .probability_model import FeatureData

#: 学習の途中経過を出さない。
_QUIET = -1
#: 古い形式の保存ファイルを読んだときの案内。
_OLD_FORMAT = "{path} は古い形式の保存ファイルです（クラスの置き場所を変える前のもの）。train で学習し直してください。"


class LightGbmModel:
    """LightGBM で学習・予測する（設計書 12）。``ProbabilityModel`` を守る。

    多クラス分類（``LightGbmMulticlassModel``）は、このクラスの目的関数・目的変数の渡し方・確率の取り出し方だけを
    変えたもの。学習・保存・読み込みの手順は同じである。

    学習データに目的変数の基準（``TrainingData.baseline``）があれば、それを出発点（``init_score``）にして、
    基準からの上げ下げだけを学ぶ（既存モデルの修正計画の 1・2）。予測では、木の出した値に基準を足して確率に戻す。
    基準を使って学んだかどうかは、モデルと一緒に保存する。
    """

    name = "LightGBM"
    file_name = "lightgbm.joblib"
    #: 目的関数。二値分類。設定ファイルでは変えられない（設計書 14）。
    objective = "binary"

    def __init__(self, settings: LightGbmSettings) -> None:
        self._settings = settings
        self._encoder: LightGbmEncoder | None = None
        self._classifier: lightgbm.LGBMClassifier | None = None
        self._baseline_check = BaselineCheck(uses_baseline=False)

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(settings.lightgbm)

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習する。検証データの当たり具合が、木を足しても良くならなくなったら止める（設計書 12 の 4）。"""
        encoder = LightGbmEncoder(self._settings.min_category_count)
        encoder.fit(train.features, train.categorical_columns)
        classifier = lightgbm.LGBMClassifier(
            objective=self.objective, verbose=_QUIET, **self._settings.params, **self._objective_params(train),
        )
        early_stopping = lightgbm.early_stopping(self._settings.early_stopping_rounds, verbose=False)
        classifier.fit(
            encoder.transform(train.features), self._label(train),
            eval_X=encoder.transform(valid.features), eval_y=self._label(valid),
            callbacks=[early_stopping], **self._baseline_arguments(train, valid),
        )
        self._encoder, self._classifier = encoder, classifier
        self._baseline_check = BaselineCheck(uses_baseline=train.baseline is not None)
        return self

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの、目的変数が 1 になる確率（設計書 12 の 5）。基準を使って学んだモデルは、基準を足して確率に戻す。"""
        encoder, classifier = self._trained()
        encoded = encoder.transform(data.features)
        if not self._baseline_check.uses_baseline:
            return self._probabilities(classifier.predict_proba(encoded))
        raw = classifier.predict(encoded, raw_score=True) + self._baseline_check.values_of(data)
        return 1.0 / (1.0 + np.exp(-raw))

    @property
    def tree_count(self) -> int:
        _, classifier = self._trained()
        return int(classifier.best_iteration_ or classifier.n_estimators_)

    def save(self, path: Path) -> None:
        """学習済みの ``LGBMClassifier`` と、エンコーダーの中身（列の並びとカテゴリの一覧）、基準を使ったかを書く（設計書 12 の 6）。

        エンコーダーは素の辞書にして書く。オブジェクトのまま pickle すると、クラスの置き場所が変わったときに
        読めなくなるため。
        """
        encoder, classifier = self._trained()
        joblib.dump({
            "encoder": encoder.state(), "classifier": classifier,
            "uses_baseline": self._baseline_check.uses_baseline,
        }, path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        """``save()`` で書いたファイルを読む。古い形式（エンコーダーをオブジェクトのまま書いたもの）は読めない。

        基準を使ったかの印が無いファイル（基準を足す前に保存したもの）は、基準なしで学んだものとして読む。
        """
        try:
            saved: dict[str, Any] = joblib.load(path)
        except ModuleNotFoundError as error:
            raise ValueError(_OLD_FORMAT.format(path=path)) from error
        if not isinstance(saved["encoder"], dict):
            raise ValueError(_OLD_FORMAT.format(path=path))
        model = cls(settings.lightgbm)
        model._encoder = LightGbmEncoder.from_state(saved["encoder"])
        model._classifier = saved["classifier"]
        model._baseline_check = BaselineCheck(uses_baseline=bool(saved.get("uses_baseline", False)))
        return model

    def _baseline_arguments(self, train: TrainingData, valid: TrainingData) -> dict[str, Any]:
        """``fit`` に足す引数。基準があれば、学習データと検証データの出発点（``init_score``）にする。"""
        if train.baseline is None:
            return {}
        return {
            "init_score": train.baseline.array(),
            "eval_init_score": [BaselineCheck(uses_baseline=True).values_of(valid)],
        }

    def _objective_params(self, train: TrainingData) -> dict[str, Any]:
        """目的関数に付けて渡す引数。二値分類には無い。"""
        return {}

    def _label(self, data: TrainingData) -> pd.Series:
        """ライブラリの ``fit`` に渡す目的変数。"""
        return data.label

    def _probabilities(self, matrix: np.ndarray) -> np.ndarray:
        """ライブラリの ``predict_proba`` の戻り値から、返す確率を取り出す。二値分類は2列目。"""
        return matrix[:, 1]

    def _trained(self) -> tuple[LightGbmEncoder, lightgbm.LGBMClassifier]:
        if self._encoder is None or self._classifier is None:
            raise RuntimeError("LightGBM のモデルがまだ学習していません（fit か load を先に呼んでください）")
        return self._encoder, self._classifier
