"""2つのモデルの予測確率を平均する。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from .class_probability_model import ClassProbabilityModel
from .probability_model import FeatureData, ProbabilityModel

#: アンサンブルに入れられるモデル（二値分類か多クラス分類）。
Member = ProbabilityModel | ClassProbabilityModel


class EnsembleModel:
    """``ProbabilityModel``（か ``ClassProbabilityModel``）を守るモデルの予測確率を平均する（アンサンブル。設計書 03 の 6）。

    確率が1列（二値分類。1頭ずつの1つの確率）でも、クラスごとの列（多クラス分類。行数 × クラスの数）でも、
    モデルごとの確率を重ねて同じ位置どうしで平均する（荒れ具合の設計書 03）。
    平均のしかた（単純な平均か、重みを付けるか）は設計書でまだ決まっていないので、いまは単純な平均。
    """

    def __init__(self, members: Sequence[Member]) -> None:
        if not members:
            raise ValueError("アンサンブルに入れるモデルがありません")
        self._members = tuple(members)

    @property
    def members(self) -> tuple[Member, ...]:
        return self._members

    def predict_members(self, data: FeatureData) -> dict[str, np.ndarray]:
        """モデルごとの予測確率。鍵はモデルの名前（LightGBM・CatBoost）。"""
        return {member.name: member.predict_proba(data) for member in self._members}

    def combine(self, member_probabilities: Mapping[str, np.ndarray]) -> np.ndarray:
        """モデルごとの確率を平均して、1つの確率にする。形はモデルごとの確率と同じ。"""
        stacked = np.stack(list(member_probabilities.values()), axis=0)
        return stacked.mean(axis=0)

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """モデルごとの確率の平均（1頭ずつの確率、またはクラスごとの確率）。"""
        return self.combine(self.predict_members(data))
