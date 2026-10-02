"""距離に使う行列の作り方の方針。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..setting import (
    ENCODING_OUT_RATE, ENCODING_ONE_HOT, SCALING_RANK, SCALING_STANDARD, WEIGHTING_AUC, WEIGHTING_NONE,
    BuyOrFadeSettings,
)
from .auc_weighting import AucWeighting
from .equal_weighting import EqualWeighting
from .one_hot_encoding import OneHotEncoding
from .out_rate_encoding import OutRateEncoding
from .rank_scaling import RankScaling
from .standard_scaling import StandardScaling


@dataclass(frozen=True)
class MatrixOptions:
    """特徴量の表を距離に使う行列にするときの方針（設計書 12・14）。``FeatureMatrix`` に渡す。

    方針の名前（``scaling``・``categorical``・``column_weighting``）から、使う部品を作る。
    """

    excluded: Sequence[str]
    group_weights: Mapping[str, float]
    add_missing_flags: bool
    scaling: str = SCALING_STANDARD
    categorical: str = ENCODING_ONE_HOT
    column_weighting: str = WEIGHTING_NONE
    column_weighting_keep: int = 0

    @classmethod
    def from_settings(cls, settings: BuyOrFadeSettings) -> MatrixOptions:
        return cls(settings.excluded_features, settings.group_weights, settings.add_missing_flags,
                   settings.scaling, settings.categorical_encoding,
                   settings.column_weighting, settings.column_weighting_keep)

    def new_scaling(self) -> StandardScaling | RankScaling:
        """数の列のそろえ方。"""
        return RankScaling() if self.scaling == SCALING_RANK else StandardScaling()

    def new_encoding(self) -> OneHotEncoding | OutRateEncoding:
        """カテゴリの列の直し方。"""
        return OutRateEncoding() if self.categorical == ENCODING_OUT_RATE else OneHotEncoding()

    def new_weighting(self) -> EqualWeighting | AucWeighting:
        """列ごとの重みの決め方。"""
        return AucWeighting(self.column_weighting_keep) if self.column_weighting == WEIGHTING_AUC else EqualWeighting()
