"""モデルごとの確率から、予測の表を作る。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, TrainingData

#: 予測の表の列の名前。
WINDOW, PART, SEGMENT = "区切り", "期間", "区分"
PREDICTION_COLUMN = "確率"
#: 期間の値（検証・テスト）。
PART_VALID, PART_TEST = "検証", "テスト"
#: 予測の表に写す ID 列。
_ID_COLUMNS = (RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO)


class PredictionFrame:
    """1つの区切り・1つの区分・1つの期間（検証かテスト）の予測を、1行 = 1頭の表にする。

    列は 区切り・期間・区分・レースID・開催日・馬ID・馬番、モデルごとの確率（LightGBM・CatBoost）、
    その平均（``PREDICTION_COLUMN``）。評価用の列や目的変数は、読む側が学習データの表と行で突き合わせる。
    """

    def build(self, data: TrainingData, member_probabilities: Mapping[str, np.ndarray],
              window: str, part: str, segment: str) -> pd.DataFrame:
        ids = data.ids[[column for column in _ID_COLUMNS if column in data.ids.columns]]
        average = np.mean(np.stack(list(member_probabilities.values()), axis=0), axis=0)
        frame = ids.assign(**member_probabilities, **{PREDICTION_COLUMN: average})
        return frame.assign(**{WINDOW: window, PART: part, SEGMENT: segment})
