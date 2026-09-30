"""学習・評価のデータの、3着以内の確率。"""

import numpy as np
import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import FIELD_SIZE, RACE_ID
from yosou.shared.feature.value_types import as_numbers

from .payback_rules import FULL_PLACE_FIELD


class PlaceProbability:
    """3着以内の確率。馬券外モデルは 1−確率。全頭がそろったレースだけ、合計を3（7頭以下は2）にそろえ直す。

    1頭ずつ学習した確率は、同じレースで足しても3にならない。そろえると、同じレースの馬どうしの比が正しくなる。
    人気範囲や馬の条件で一部の馬だけになったレースは、合計の基準が無いのでそのまま使う。
    """

    def of(self, data: TrainingData, probability: np.ndarray, target: str) -> np.ndarray:
        coming = 1 - probability if target == "馬券外" else probability
        frame = pd.DataFrame({
            "race": data.ids[RACE_ID].to_numpy(), "p": coming,
            "field": as_numbers(data.evaluation[FIELD_SIZE]).to_numpy(),
        })
        grouped = frame.groupby("race", sort=False)
        complete = grouped["p"].transform("size").to_numpy() == frame["field"].to_numpy()
        places = np.where(frame["field"].to_numpy() >= FULL_PLACE_FIELD, 3.0, 2.0)
        scale = places / grouped["p"].transform("sum").to_numpy()
        return np.where(complete, np.clip(coming * scale, 0.0, 1.0), coming)
