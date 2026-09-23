"""予測の表に、学習データの表を突き合わせる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData

from ..walk_forward import PART

#: 突き合わせた表に足す列（正解 = その予想の目的変数、基準の確率 = オッズから作った基準）。
LABEL = "正解"
BASE_PROBABILITY = "基準の確率"
#: 突き合わせる鍵。
_KEYS = [RACE_ID, HORSE_ID]


class PredictionJoin:
    """予測の表（``walk_forward`` の出力）に、学習データの表の評価用の列・目的変数・基準の確率を並べる。

    予測の表にある列（開催日・馬番 など）は予測の表のものを使い、学習データの表の同じ名前の列は付けない。
    """

    def __init__(self, data: TrainingData) -> None:
        base = data.baseline.probabilities().to_numpy() if data.baseline is not None else np.nan
        self._table = pd.concat([data.ids[_KEYS], data.evaluation, data.targets], axis=1).assign(**{
            LABEL: data.label.to_numpy(), BASE_PROBABILITY: base,
        })

    def of(self, predictions: pd.DataFrame, part: str | None = None) -> pd.DataFrame:
        """``part``（検証かテスト）の行だけにして突き合わせる。None なら両方。"""
        chosen = predictions if part is None else predictions[predictions[PART] == part]
        extra = [column for column in self._table.columns if column in _KEYS or column not in chosen.columns]
        return chosen.merge(self._table[extra], on=_KEYS, how="left")
