"""手本の学習データに、まとまり W（重賞の格と実績）と K（その重賞の傾向）を足す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import FeatureCatalog
from yosou.stakes_tendency_top3.feature import K_FEATURES

from .graded_features import W_CATEGORICAL, W_FEATURES, W_NAMES

_KEYS = ["race_id", "horse_id"]
#: K の列の名前。
K_NAMES: tuple[str, ...] = tuple(feature.name for feature in K_FEATURES)


class GradedTableBuilder:
    """手本の学習データ（全レース）に W と K の列を（レースID, 馬ID）で突き合わせて足し、特徴量の一覧も広げる。

    - ``materials``: W の表（``GradedMaterialReader`` が読んだもの。1行 = 1頭の出走）。
    - ``tendency``: K の表（引退した予想の重賞だけの学習データから取り出した K の列と鍵）。重賞でない行の K は欠損値になる。
    """

    def extra(self, base: TrainingData, materials: pd.DataFrame, tendency: pd.DataFrame) -> pd.DataFrame:
        """``base`` と同じ行の並び・index の、W と K の列だけの表。"""
        keys = pd.DataFrame({"race_id": base.ids[RACE_ID].astype(str).to_numpy(),
                             "horse_id": base.ids[HORSE_ID].astype(str).to_numpy()})
        aligned = keys.merge(materials, on=_KEYS, how="left").merge(tendency, on=_KEYS, how="left")
        if len(aligned) != len(keys):
            raise ValueError("W・K の表に、同じ（レースID, 馬ID）の行が2つ以上あります")
        missing = aligned[W_NAMES[0]].isna().sum()
        if missing:
            raise ValueError(f"W の無い行が {missing} 行あります（事実表と学習データの行が合いません）")
        columns = [*W_NAMES, *K_NAMES]
        frame = aligned[columns].set_axis(base.features.index)
        numeric = [name for name in columns if name not in W_CATEGORICAL]
        frame[numeric] = frame[numeric].astype("float64")
        return frame

    def attach(self, base: TrainingData, extra: pd.DataFrame) -> TrainingData:
        """``extra``（``extra`` で作った表）を特徴量に足した学習データ。カテゴリの W は category 型にする。"""
        added = extra.copy()
        for name in W_CATEGORICAL:
            added[name] = added[name].astype("category")
        features = pd.concat([base.features, added], axis=1)
        catalog = FeatureCatalog(base.catalog.features + W_FEATURES + K_FEATURES)
        return replace(base, features=features, catalog=catalog)
