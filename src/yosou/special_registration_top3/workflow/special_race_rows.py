"""特別競走の行と、行ごとの確率の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from yosou.shared.dataset import TrainingData


@dataclass(frozen=True)
class SpecialRaceRows:
    """特別競走の行（テスト期間のうち Y = 1 の行）と、行ごとの確率（モデルの名前 → 確率）。区切りをまたいでつなげられる。"""

    data: TrainingData
    probabilities: dict[str, np.ndarray]

    def joined(self, other: SpecialRaceRows) -> SpecialRaceRows:
        """2つをつなげたもの（全期間の当たり具合を測るため）。"""
        data = TrainingData(
            pd.concat([self.data.ids, other.data.ids]), pd.concat([self.data.features, other.data.features]),
            pd.concat([self.data.targets, other.data.targets]), pd.concat([self.data.evaluation, other.data.evaluation]),
            self.data.catalog, self.data.label_name, self.data.class_labels,
        )
        probabilities = {name: np.concatenate([self.probabilities[name], other.probabilities[name]]) for name in self.probabilities}
        return SpecialRaceRows(data, probabilities)
