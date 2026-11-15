"""重賞の行に重みを付けて学ぶ作り方1つ。"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from yosou.shared.dataset import TOP3, TrainingData, WinTargetData

from ..variants import ModelVariant
from .graded_features import IS_GRADED


@dataclass(frozen=True)
class GradedVariant(ModelVariant):
    """重賞の予想の確かめで比べる作り方1つ（``ModelVariant`` に、目的変数と重賞の行の重みを足したもの）。

    - ``label``: 目的変数（3着以内 か 1着）。1着なら ``WinTargetData`` で目的変数と基準を持ち替える。
    - ``graded_weight``: 重賞の行の重み（ほかの行は 1）。1 なら重みを付けない（今の予想と同じ学び方）。
    """

    label: str = TOP3
    graded_weight: float = 1.0

    def prepare(self, data: TrainingData) -> TrainingData:
        labeled = data if self.label == TOP3 else WinTargetData().training(data)
        prepared = super().prepare(labeled)
        if self.graded_weight == 1.0:
            return prepared
        graded = labeled.features[IS_GRADED].eq(1.0).to_numpy()
        weight = pd.Series(np.where(graded, self.graded_weight, 1.0), index=labeled.features.index)
        return replace(prepared, weight=weight)
