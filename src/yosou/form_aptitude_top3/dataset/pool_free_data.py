"""学習データ・予測用データから、券種ごとのオッズから見た支持（まとまり N）を外す。"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.dataset import PredictionData, TrainingData

from ..feature import CATALOG, POOL_SUPPORT_NAMES


class PoolFreeData:
    """N の6列を外し、特徴量の一覧を今の材料（``CATALOG``。79個）にしたデータを返す。

    当日に券種のオッズが無いレースは、N を使わないモデル（``POOL_FREE_FOLDER`` に置く）で予測する。
    そのモデルは、N を足した学習データ（``pool_dataset_builder``）からこのクラスで N を外して学ぶので、
    学習データを2回作らなくてよい。
    """

    def training(self, data: TrainingData) -> TrainingData:
        return replace(data, features=data.features.drop(columns=list(POOL_SUPPORT_NAMES), errors="ignore"),
                       catalog=CATALOG)

    def prediction(self, data: PredictionData) -> PredictionData:
        return replace(data, features=data.features.drop(columns=list(POOL_SUPPORT_NAMES), errors="ignore"),
                       catalog=CATALOG)
