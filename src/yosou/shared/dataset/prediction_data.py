"""予測用データの表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..feature import FeatureCatalog, PredictionTiming
from .baseline_logit import BaselineLogit


@dataclass(frozen=True)
class PredictionData:
    """予測用データ（1行 = 1頭）。1レースの出走馬について、``timing`` の時点で使う特徴量だけを持つ。

    学習データから、目的変数と評価用の列を除いた形（設計書 08 の 2）。
    ``catalog`` は ``features`` の元になった特徴量の一覧。``baseline`` は目的変数の基準（ロジット）で、
    その時点で使えなければ（木曜など）None。
    ``market`` は、予測の結果に足す材料（複勝オッズ・頭数・オッズから見た勝率・2着以内率・3着以内率）。
    複勝を買う期待値を出すのに使い、モデルには渡さない。オッズの無い時点では欠損値。
    """

    ids: pd.DataFrame
    features: pd.DataFrame
    timing: PredictionTiming
    catalog: FeatureCatalog
    baseline: BaselineLogit | None = None
    market: pd.DataFrame | None = None

    def __len__(self) -> int:
        return len(self.ids)

    @property
    def categorical_columns(self) -> tuple[str, ...]:
        """特徴量のうち、カテゴリ特徴量の名前（列の並び順）。"""
        return self.catalog.categorical_columns_of(self.features)

    def where(self, rows: pd.Series) -> PredictionData:
        """``rows``（行ごとの真偽）が真の行だけの予測用データ。区分ごとに別のモデルで予測するときに使う。"""
        baseline = self.baseline.at(rows) if self.baseline is not None else None
        market = self.market[rows] if self.market is not None else None
        return PredictionData(self.ids[rows], self.features[rows], self.timing, self.catalog, baseline, market)
