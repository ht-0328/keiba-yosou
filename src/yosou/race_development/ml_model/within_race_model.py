"""二値分類のモデルを包み、確率をレースの中で合計 1 にそろえる。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar, Self

import numpy as np

from yosou.shared.dataset import RACE_ID, TrainingData
from yosou.shared.ml_model import FeatureData, ProbabilityModel
from yosou.shared.setting import HyperparameterSettings

from .race_softmax import RaceSoftmax
from .temperature_fitter import TemperatureFitter
from .validation_halves import ValidationHalves

#: 温度を書くファイルの名前の後ろ（モデルのファイルの名前に付ける）。
_TEMPERATURE_SUFFIX = ".temperature.json"


class WithinRaceModel:
    """共通の二値のモデル1つを包み、1頭ずつの確率を、レースの中で合計 1 にそろえる（設計書 03 の 2・05 の図3）。

    ① 先頭と ⑦ 1着で使う。``fit`` では、検証データを前半と後半に分け、前半で早期終了しながら中のモデルを学習し、
    後半で温度を決める。``predict_proba`` では、中のモデルの確率を raw スコアに戻し、温度で割ってレースごとに合計 1 にする。
    ``ProbabilityModel`` を守るので、共通の ``TrainingWorkflow``・``EnsembleModel``・``ModelRepository`` がそのまま使える。
    中のモデルのクラスは、子のクラス（``LightGbmWithinRaceModel``・``CatBoostWithinRaceModel``）が決める。
    """

    name: ClassVar[str]
    file_name: ClassVar[str]
    #: 中のモデルのクラス（共通の ``LightGbmModel`` か ``CatBoostModel``）。
    inner_type: ClassVar[type[ProbabilityModel]]

    def __init__(self, inner: ProbabilityModel, temperature: float = 1.0) -> None:
        self._inner = inner
        self._temperature = temperature
        self._softmax = RaceSoftmax()

    @classmethod
    def from_settings(cls, settings: HyperparameterSettings) -> Self:
        return cls(cls.inner_type.from_settings(settings))

    @property
    def temperature(self) -> float:
        return self._temperature

    def fit(self, train: TrainingData, valid: TrainingData) -> Self:
        first_half, second_half = ValidationHalves().split(valid)
        self._inner.fit(train, first_half)
        raw = self._softmax.raw_of(self._inner.predict_proba(second_half))
        race_ids = second_half.ids[RACE_ID].to_numpy()
        self._temperature = TemperatureFitter().fit(raw, race_ids, second_half.label.to_numpy())
        return self

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの確率。同じレースの行を足すと 1（``data`` にはレースの全頭を入れる）。"""
        raw = self._softmax.raw_of(self._inner.predict_proba(data))
        return self._softmax.apply(raw, data.ids[RACE_ID].to_numpy(), self._temperature)

    @property
    def tree_count(self) -> int:
        return self._inner.tree_count

    def save(self, path: Path) -> None:
        """中のモデルを ``path`` に、温度を隣の小さな JSON に書く（設計書 12・13 の 6）。"""
        self._inner.save(path)
        self._temperature_path(path).write_text(json.dumps({"temperature": self._temperature}) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path, settings: HyperparameterSettings) -> Self:
        saved = json.loads(cls._temperature_path(path).read_text(encoding="utf-8"))
        return cls(cls.inner_type.load(path, settings), float(saved["temperature"]))

    @staticmethod
    def _temperature_path(path: Path) -> Path:
        return Path(path).with_name(Path(path).name + _TEMPERATURE_SUFFIX)
