"""2つのモデルの予測確率を平均する。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from .probability_model import FeatureData, ProbabilityModel


class EnsembleModel:
    """``ProbabilityModel`` を守るモデルの予測確率を平均する（アンサンブル。設計書 03 の 6）。

    平均のしかた（単純な平均か、重みを付けるか）は設計書でまだ決まっていないので、いまは単純な平均。
    """

    def __init__(self, members: Sequence[ProbabilityModel]) -> None:
        if not members:
            raise ValueError("アンサンブルに入れるモデルがありません")
        self._members = tuple(members)

    @property
    def members(self) -> tuple[ProbabilityModel, ...]:
        return self._members

    def predict_members(self, data: FeatureData) -> dict[str, np.ndarray]:
        """モデルごとの「3着以内に入る確率」。鍵はモデルの名前（LightGBM・CatBoost）。"""
        return {member.name: member.predict_proba(data) for member in self._members}

    def combine(self, member_probabilities: Mapping[str, np.ndarray]) -> np.ndarray:
        """モデルごとの確率を平均して、1つの確率にする。"""
        stacked = np.vstack(list(member_probabilities.values()))
        return stacked.mean(axis=0)

    def predict_proba(self, data: FeatureData) -> np.ndarray:
        """1頭ずつの「3着以内に入る確率」（モデルごとの確率の平均）。"""
        return self.combine(self.predict_members(data))
