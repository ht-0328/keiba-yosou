"""全頭の予想①の学習データから、人気帯の行と目的変数・基準を持ち替えた学習データを作る（②危険な人気馬・③穴馬）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import TOP3, BaselineLogit, FinishPowerFreeData, TrainingData
from yosou.shared.dataset.column_names import POPULARITY
from yosou.shared.feature import as_numbers

#: 目的変数の名前（②は「4着以下」、③は①と同じ「3着以内」）。
OUT_OF_TOP3 = "4着以下"
#: 人気の帯（利用者の指示: 人気馬 1〜3・中穴 4〜7・大穴 8番人気以下）。
FAVORITE_LAST, MIDDLE_LAST = 3, 7


class BandData:
    """①の学習データ（``LocalTrainingDataCache`` のもの。Q と U を含む）から、帯の行だけを残した学習データを作る。
    どちらも Q（勝ち切る材料）は外す（①の3着以内のモデルと同じ材料）。基準はオッズから見た率のロジット（①と同じ。②は符号を変える）。"""

    def favorites(self, data: TrainingData) -> TrainingData:
        """② 1〜3番人気の行。目的変数は「4着以下」（1 − 3着以内）、基準は「オッズから見た4着以下率」のロジット。"""
        rows = self._popularity(data).between(1, FAVORITE_LAST)
        chosen = FinishPowerFreeData().training(data.where(rows))
        targets = chosen.targets.assign(**{OUT_OF_TOP3: 1 - as_numbers(chosen.targets[TOP3]).astype(int)})
        baseline = None if chosen.baseline is None else BaselineLogit(-chosen.baseline.values, chosen.baseline.known_from)
        return TrainingData(chosen.ids, chosen.features, targets, chosen.evaluation, chosen.catalog, OUT_OF_TOP3,
                            chosen.class_labels, baseline)

    def longshots(self, data: TrainingData) -> TrainingData:
        """③ 4番人気以下の行。目的変数は「3着以内」、基準は①と同じ。"""
        rows = self._popularity(data) >= FAVORITE_LAST + 1
        return FinishPowerFreeData().training(data.where(rows))

    def _popularity(self, data: TrainingData) -> pd.Series:
        return as_numbers(data.evaluation[POPULARITY])
