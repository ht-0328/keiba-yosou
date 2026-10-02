"""保存した2つの学習データの表を、同じ出走の行でつないで1つにする。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import FeatureCatalog

#: 行を突き合わせる鍵。
_KEY = [RACE_ID, HORSE_ID]


class TableMerge:
    """``base`` の行（と目的変数・評価用の列・基準）に、``extra`` の同じ出走（レースID・馬ID）の特徴量を足す。

    今の材料の表（2017年から）に、馬の力の材料の表（2012年から）の M の列を足すのに使う。``extra`` に無い出走は欠損値。
    ``extra`` の列のうち ``base`` にもある列（J の4個）は足さない。特徴量の一覧は ``catalog``。
    """

    def merge(self, base: TrainingData, extra: TrainingData, catalog: FeatureCatalog) -> TrainingData:
        added = [column for column in extra.features.columns if column not in base.features.columns]
        right = pd.concat([extra.ids[_KEY].reset_index(drop=True), extra.features[added].reset_index(drop=True)], axis=1)
        aligned = base.ids[_KEY].reset_index(drop=True).merge(right.drop_duplicates(_KEY), on=_KEY, how="left")
        features = pd.concat([base.features, aligned[added].set_axis(base.features.index)], axis=1)
        return replace(base, features=features[list(catalog.names)], catalog=catalog)
