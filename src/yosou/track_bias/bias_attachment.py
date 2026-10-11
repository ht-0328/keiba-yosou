"""学習データ・予測用データに、トラックバイアスの補正（まとまり U）の5列を足す。"""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import TRACK_BIAS_FEATURES, TRACK_BIAS_NAMES

#: 学習データか予測用データ（どちらも ``ids``・``features``・``catalog`` を持つ）。
Data = TypeVar("Data", TrainingData, PredictionData)
#: 補正の表の鍵。
_KEY: list[str] = ["race_id", "horse_id"]


class BiasAttachment:
    """``data`` の行に、同じ出走（レースID・馬ID）の U の5列を足し、特徴量の一覧にも U を足す（S の ``ScoreAttachment`` と同じ形）。

    ``corrected`` はバイアスの補正の表（1行 = 1頭、列 ``race_id``・``horse_id`` と ``TRACK_BIAS_NAMES``）で、呼ぶ側が渡す。
    学習データには ``BiasHistory``（年ごとの確かめの展開の予測と、その年より前のレースだけで作った過去の傾きの表）、
    予測用データには ``RaceBiasSource``（保存した展開のモデルの予測と、元DB の終わったレースと過去の傾きの表）のもの。表に無い出走は欠損値。
    もう U があれば置き換える。
    """

    def apply(self, data: Data, corrected: pd.DataFrame) -> Data:
        keys = pd.DataFrame({"race_id": data.ids[RACE_ID].astype(str).to_numpy(), "horse_id": data.ids[HORSE_ID].astype(str).to_numpy()})
        table = corrected.reindex(columns=[*_KEY, *TRACK_BIAS_NAMES]).astype({key: str for key in _KEY}).drop_duplicates(_KEY)
        aligned = keys.merge(table, on=_KEY, how="left")[list(TRACK_BIAS_NAMES)].astype("float64")
        features = pd.concat([data.features.drop(columns=list(TRACK_BIAS_NAMES), errors="ignore"),
                              aligned.set_axis(data.features.index)], axis=1)
        return replace(data, features=features, catalog=self._catalog(data.catalog))

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        """U を足した一覧（もう U があれば、そのまま）。"""
        names = set(catalog.names)
        return FeatureCatalog(catalog.features + tuple(feature for feature in TRACK_BIAS_FEATURES if feature.name not in names))
