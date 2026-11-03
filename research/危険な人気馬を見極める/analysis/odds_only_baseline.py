"""オッズだけのモデルの確率を、人気馬の予想の出発点と、危険度の比べる相手（基準）にする。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import TypeVar

import numpy as np

from yosou.shared.dataset import BaselineLogit, PredictionData, TrainingData
from yosou.shared.feature import ODDS_FEATURES
from yosou.shared.feature.group import POPULARITY_RANK
from yosou.shared.ml_model import MEMBER_TYPES, ProbabilityModel
from yosou.shared.setting import HyperparameterSettings

#: オッズだけのモデルが使う列（人気順位・単勝オッズから見た評価・頭数。馬の情報は入れない）。
ODDS_ONLY_COLUMNS: tuple[str, ...] = (POPULARITY_RANK, *(feature.name for feature in ODDS_FEATURES), "出走頭数")
#: 確率をロジットに直すときに、0 と 1 に張り付かないように抑える幅。
_CLIP = 1e-4

Data = TypeVar("Data", TrainingData, PredictionData)


class OddsOnlyBaseline:
    """オッズの列（``ODDS_ONLY_COLUMNS``）だけで学んだ LightGBM と CatBoost の平均で、「オッズから見た4着以下の確率」を出す。

    オッズから計算した確率（Harville の式）は、人気の度合いによって実際の結果とずれる（1番人気の3着以内率を高めに出す）。
    それをそのまま基準にすると、危険度（予想 − 基準）にそのずれが混ざり、オッズの低い1番人気ほど危険に見えて、
    本当に危ない人気馬を選べない。オッズだけのモデルは、オッズから計算した確率を出発点に、実際の結果に合わせ直したもの。
    人気馬の予想は、このモデルの確率を出発点にして学び（``attach``）、危険度もこの確率と比べる。全頭の予想（3着以内・1着）の出発点にも使える
    （目的変数が何でも、学習データの基準から学ぶ）。この研究で確かめ、本番には入れていない（買い目の回収率が今の本番を超えなかった）。
    """

    def __init__(self, members: Sequence[ProbabilityModel]) -> None:
        if not members:
            raise ValueError("オッズだけのモデルがありません")
        self.members = list(members)

    @classmethod
    def fit(cls, settings: HyperparameterSettings, train: TrainingData, valid: TrainingData,
            member_types: Sequence[type[ProbabilityModel]] = MEMBER_TYPES) -> OddsOnlyBaseline:
        """学習期間で学ぶ（木を足すのを止める判断に検証期間を使う）。学習データの基準（オッズから計算した確率）を出発点にする。"""
        return cls([member_type.from_settings(settings).fit(cls._odds(train), cls._odds(valid)) for member_type in member_types])

    def probabilities(self, data: TrainingData | PredictionData) -> np.ndarray:
        """1頭ずつの、オッズから見た4着以下の確率（2つのモデルの平均）。"""
        odds = self._odds(data)
        return np.mean([member.predict_proba(odds) for member in self.members], axis=0)

    def attach(self, data: Data) -> Data:
        """基準を、このモデルの確率（のロジット）に置き換えたデータ。オッズの分からない時点（基準が無い）のデータは渡せない。"""
        if data.baseline is None:
            raise ValueError("オッズの分かる時点（前日・当日）のデータを渡してください")
        clipped = np.clip(self.probabilities(data), _CLIP, 1 - _CLIP)
        values = data.baseline.values.copy()
        values[:] = np.log(clipped / (1 - clipped))
        return replace(data, baseline=BaselineLogit(values, data.baseline.known_from))

    @staticmethod
    def _odds(data: Data) -> Data:
        """オッズの列だけにしたデータ。"""
        missing = [column for column in ODDS_ONLY_COLUMNS if column not in data.features.columns]
        if missing:
            raise ValueError(f"データに無いオッズの列があります: {'・'.join(missing)}")
        return replace(data, features=data.features[list(ODDS_ONLY_COLUMNS)])
