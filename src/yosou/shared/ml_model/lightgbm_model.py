"""LightGBM で学習・予測する。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import joblib
import lightgbm
import numpy as np

from ..dataset import TrainingData
from ..setting import HyperparameterSettings, LightGbmSettings
from .lightgbm_encoder import LightGbmEncoder
from .probability_model import FeatureData

#: 目的関数。二値分類。設定ファイルでは変えられない（設計書 14）。
_OBJECTIVE = "binary"
#: 学習の途中経過を出さない。
_QUIET = -1
#: 古い形式の保存ファイルを読んだときの案内。
_OLD_FORMAT = "{path} は古い形式の保存ファイルです（クラスの置き場所を変える前のもの）。train で学習し直してください。"


class LightGbmModel:
    """LightGBM で学習・予測する（設計書 12）。``ProbabilityModel`` を守る。"""

    name = "LightGBM"
    file_name = "lightgbm.joblib"

    def __init__(self, settings: LightGbmSettings) -> None:
        self._settings = settings
        self._encoder: LightGbmEncoder | None = None
        self._classifier: lightgbm.LGBMClassifier | None = None

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(settings.lightgbm)

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        """学習する。検証データの当たり具合が、木を足しても良くならなくなったら止める（設計書 12 の 4）。"""
        encoder = LightGbmEncoder(self._settings.min_category_count)
        encoder.fit(train.features, train.categorical_columns)
        classifier = lightgbm.LGBMClassifier(
            objective=_OBJECTIVE, verbose=_QUIET, **self._settings.params,
        )
        early_stopping = lightgbm.early_stopping(self._settings.early_stopping_rounds, verbose=False)
        classifier.fit(
            encoder.transform(train.features), train.label,
            eval_X=encoder.transform(valid.features), eval_y=valid.label,
            callbacks=[early_stopping],
        )
        self._encoder, self._classifier = encoder, classifier
        return self

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの、目的変数が 1 になる確率（設計書 12 の 5）。"""
        encoder, classifier = self._trained()
        return classifier.predict_proba(encoder.transform(data.features))[:, 1]

    @property
    def tree_count(self) -> int:
        _, classifier = self._trained()
        return int(classifier.best_iteration_ or classifier.n_estimators_)

    def save(self, path: Path) -> None:
        """学習済みの ``LGBMClassifier`` と、エンコーダーの中身（列の並びとカテゴリの一覧）を書く（設計書 12 の 6）。

        エンコーダーは素の辞書にして書く。オブジェクトのまま pickle すると、クラスの置き場所が変わったときに
        読めなくなるため。
        """
        encoder, classifier = self._trained()
        joblib.dump({"encoder": encoder.state(), "classifier": classifier}, path)

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        """``save()`` で書いたファイルを読む。古い形式（エンコーダーをオブジェクトのまま書いたもの）は読めない。"""
        try:
            saved: dict[str, Any] = joblib.load(path)
        except ModuleNotFoundError as error:
            raise ValueError(_OLD_FORMAT.format(path=path)) from error
        if not isinstance(saved["encoder"], dict):
            raise ValueError(_OLD_FORMAT.format(path=path))
        model = cls(settings.lightgbm)
        model._encoder = LightGbmEncoder.from_state(saved["encoder"])
        model._classifier = saved["classifier"]
        return model

    def _trained(self) -> tuple[LightGbmEncoder, lightgbm.LGBMClassifier]:
        if self._encoder is None or self._classifier is None:
            raise RuntimeError("LightGBM のモデルがまだ学習していません（fit か load を先に呼んでください）")
        return self._encoder, self._classifier
