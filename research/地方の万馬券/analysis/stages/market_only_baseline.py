"""基準「市場の割れ方だけの予想」を、同じ手順で学んで測る。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from yosou.shared.dataset import SplitData, TrainingData
from yosou.shared.feature import FeatureCatalog
from yosou.shared.ml_model import CLASS_MEMBER_TYPES, EnsembleModel, Member
from yosou.shared.setting import HyperparameterSettings


class MarketOnlyBaseline:
    """特徴量を ``names``（オッズの形 B と頭数。市場の割れ方だけ）に絞り、④と同じ設定・同じ学習データ・検証データで
    LightGBM と CatBoost を学んで、テストデータの4つの確率を出す。④の材料（出走馬のばらつき・1番人気の危うさ・過去の荒れ率・当日の馬場傾向）が、
    市場の割れ方以上に荒れ具合を当てているかを見るための基準。モデルは保存しない。"""

    def __init__(self, settings: HyperparameterSettings, names: Sequence[str],
                 member_types: Sequence[type[Member]] = CLASS_MEMBER_TYPES) -> None:
        self._settings = settings
        self._names = tuple(names)
        self._member_types = tuple(member_types)

    def fit_predict(self, split: SplitData, test: TrainingData) -> np.ndarray:
        """``split.train``・``split.valid`` で学び、``test`` の行ごとの4つの確率（クラスの番号の順）。"""
        train, valid = self._only(split.train), self._only(split.valid)
        members = [model_type.from_settings(self._settings).fit(train, valid) for model_type in self._member_types]
        return EnsembleModel(members).predict_proba(self._only(test))

    def _only(self, data: TrainingData) -> TrainingData:
        names = [name for name in self._names if name in data.features.columns]
        catalog = FeatureCatalog(tuple(feature for feature in data.catalog.features if feature.name in names))
        return TrainingData(data.ids, data.features[names], data.targets, data.evaluation, catalog, data.label_name, data.class_labels, data.baseline)
