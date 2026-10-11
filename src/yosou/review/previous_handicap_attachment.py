"""学習データ・予測用データに、前走の不利（まとまり X）の列を足す。"""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import PREVIOUS_HANDICAP_FEATURES, PREVIOUS_HANDICAP_NAMES

#: 学習データか予測用データ（どちらも ``ids``・``features``・``catalog`` を持つ）。
Data = TypeVar("Data", TrainingData, PredictionData)
_KEY: list[str] = ["race_id", "horse_id"]


class PreviousHandicapAttachment:
    """``data`` の行に、同じ出走（レースID・馬ID）の X の5列を足し、特徴量の一覧にも X を足す（S の ``ScoreAttachment`` と同じ形）。

    ``previous`` は前走の不利の表（``PreviousHandicapColumns`` の表、または予測用に ``StoredHandicapLookup`` が作った表）。表に無い出走は欠損値。
    もう X があれば置き換える。
    """

    def apply(self, data: Data, previous: pd.DataFrame) -> Data:
        keys = pd.DataFrame({"race_id": data.ids[RACE_ID].astype(str).to_numpy(), "horse_id": data.ids[HORSE_ID].astype(str).to_numpy()})
        table = previous.reindex(columns=[*_KEY, *PREVIOUS_HANDICAP_NAMES]).astype({key: str for key in _KEY}).drop_duplicates(_KEY)
        aligned = keys.merge(table, on=_KEY, how="left")[list(PREVIOUS_HANDICAP_NAMES)].astype("float64")
        features = pd.concat([data.features.drop(columns=list(PREVIOUS_HANDICAP_NAMES), errors="ignore"),
                              aligned.set_axis(data.features.index)], axis=1)
        return replace(data, features=features, catalog=self._catalog(data.catalog))

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        names = set(catalog.names)
        return FeatureCatalog(catalog.features + tuple(feature for feature in PREVIOUS_HANDICAP_FEATURES if feature.name not in names))
