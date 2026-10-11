"""学習データ・予測用データに、展開スコア（まとまり S）の 5列を足す。"""

from __future__ import annotations

from dataclasses import replace
from typing import TypeVar

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, PredictionData, TrainingData
from yosou.shared.feature import FeatureCatalog

from .features import DEVELOPMENT_SCORE_FEATURES, DEVELOPMENT_SCORE_NAMES

#: 学習データか予測用データ（どちらも ``ids``・``features``・``catalog`` を持つ）。
Data = TypeVar("Data", TrainingData, PredictionData)
#: 展開スコアの表の鍵。
_KEY: list[str] = ["race_id", "horse_id"]


class ScoreAttachment:
    """``data`` の行に、同じ出走（レースID・馬ID）の S の 5列を足し、特徴量の一覧にも S を足す（P の ``PaceAttachment`` と同じ形）。

    ``scored`` は展開スコアの表（1行 = 1頭、列 ``race_id``・``horse_id`` と ``DEVELOPMENT_SCORE_NAMES``）で、呼ぶ側が渡す。
    学習データには ``ScoreHistory``（年ごとの確かめの予測と、その年より前のレースだけで作った表 G）、予測用データには
    ``RaceScoreSource``（保存した展開のモデルの予測と、元DB の全出走から作った表 G）のもの。表に無い出走は欠損値。
    もう S があれば置き換える。
    """

    def apply(self, data: Data, scored: pd.DataFrame) -> Data:
        keys = pd.DataFrame({"race_id": data.ids[RACE_ID].astype(str).to_numpy(), "horse_id": data.ids[HORSE_ID].astype(str).to_numpy()})
        table = scored.reindex(columns=[*_KEY, *DEVELOPMENT_SCORE_NAMES]).astype({key: str for key in _KEY}).drop_duplicates(_KEY)
        aligned = keys.merge(table, on=_KEY, how="left")[list(DEVELOPMENT_SCORE_NAMES)].astype("float64")
        features = pd.concat([data.features.drop(columns=list(DEVELOPMENT_SCORE_NAMES), errors="ignore"),
                              aligned.set_axis(data.features.index)], axis=1)
        return replace(data, features=features, catalog=self._catalog(data.catalog))

    def _catalog(self, catalog: FeatureCatalog) -> FeatureCatalog:
        """S を足した一覧（もう S があれば、そのまま）。"""
        names = set(catalog.names)
        return FeatureCatalog(catalog.features + tuple(feature for feature in DEVELOPMENT_SCORE_FEATURES if feature.name not in names))
