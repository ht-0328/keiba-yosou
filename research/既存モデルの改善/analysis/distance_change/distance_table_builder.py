"""元の学習データの表に、距離の変更の傾向（まとまり R）を足す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import DISTANCE_CHANGE_KEY, HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import DISTANCE_CHANGE_FEATURES, FeatureCatalog
from yosou.shared.feature.history import DISTANCE_CHANGE_NAMES


class DistanceTableBuilder:
    """``base`` の行（目的変数・評価用の列・基準もそのまま）に、同じ出走（レースID・馬ID）の R の 7列を足す。

    ``records`` は予想のパッケージの ``DistanceChangeRecordsLoader.read`` の表（race_id・horse_id と 7列）。
    表に無い出走は欠損値。特徴量の一覧も 7個広げる。元の表にもう同じ列があれば置き換える。
    """

    def build(self, base: TrainingData, records: pd.DataFrame) -> TrainingData:
        race_id, horse_id = DISTANCE_CHANGE_KEY
        keys = pd.DataFrame({race_id: base.ids[RACE_ID].astype(str).to_numpy(), horse_id: base.ids[HORSE_ID].astype(str).to_numpy()})
        records = records.astype({race_id: str, horse_id: str}).drop_duplicates(DISTANCE_CHANGE_KEY)
        aligned = keys.merge(records, on=DISTANCE_CHANGE_KEY, how="left")
        added = aligned[list(DISTANCE_CHANGE_NAMES)].astype("float64").set_axis(base.features.index)
        features = pd.concat([base.features.drop(columns=list(DISTANCE_CHANGE_NAMES), errors="ignore"), added], axis=1)
        kept = tuple(feature for feature in base.catalog.features if feature.name not in DISTANCE_CHANGE_NAMES)
        return replace(base, features=features, catalog=FeatureCatalog(kept + DISTANCE_CHANGE_FEATURES))
