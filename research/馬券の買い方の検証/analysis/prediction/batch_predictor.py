"""期間の学習データから予測の表を作る決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from yosou.shared.dataset import TrainingData


class BatchPredictor(Protocol):
    """期間ぶんの学習データ（``TrainingData``）を受け取り、保存済みモデルの予測を付けた表を返す。

    1頭ごとの予想は ``RunnerBatchPredictor``、レース単位の予想は ``RaceBatchPredictor`` が守る。
    """

    def predict(self, data: TrainingData) -> pd.DataFrame:
        """ID 列・評価用の列・予測の列を持つ表（行の並びは ``data`` と同じ）。"""
        ...
