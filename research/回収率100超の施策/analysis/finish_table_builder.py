"""元の学習データの表に、勝ち切る材料（まとまり Q）を足す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import FeatureCatalog

from .finish_columns import FINISH_FEATURES, FINISH_NAMES


class FinishTableBuilder:
    """``base`` の行（目的変数・評価用の列・基準もそのまま）に、同じ出走（レースID・馬ID）の勝ち切る材料の 10列を足す。

    ``records`` は予想のパッケージの ``FinishRecordsLoader.read`` の表（race_id・horse_id と 10列）。
    表に無い出走は欠損値。特徴量の一覧も 10個広げる。元の表にもう同じ列があれば置き換える。
    """

    def build(self, base: TrainingData, records: pd.DataFrame) -> TrainingData:
        extra = records
        keys = pd.DataFrame({"race_id": base.ids[RACE_ID].astype(str).to_numpy(), "horse_id": base.ids[HORSE_ID].astype(str).to_numpy()})
        aligned = keys.merge(extra.astype({"race_id": str, "horse_id": str}).drop_duplicates(["race_id", "horse_id"]),
                             on=["race_id", "horse_id"], how="left")
        added = aligned[list(FINISH_NAMES)].astype("float64").set_axis(base.features.index)
        features = pd.concat([base.features.drop(columns=list(FINISH_NAMES), errors="ignore"), added], axis=1)
        kept = tuple(feature for feature in base.catalog.features if feature.name not in FINISH_NAMES)
        return replace(base, features=features, catalog=FeatureCatalog(kept + FINISH_FEATURES))
