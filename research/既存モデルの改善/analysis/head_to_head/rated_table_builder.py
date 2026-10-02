"""学習データの表に、対戦レーティングの7列を足す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import HEAD_TO_HEAD_FEATURES, FeatureCatalog
from yosou.shared.feature.head_to_head import RatingTableBuilder


class RatedTableBuilder:
    """元の表（``base``）の行に、予想のパッケージと同じ部品（``RatingTableBuilder``）で作った対戦レーティングの7列を足す。

    ``runs`` は 2011年からの中央の平地の全出走（``HeadToHeadRunRepository`` で読んだもの）。レース内の順位・偏差・平均との差は、
    表の同じレースの行（出走した馬）どうしで比べる。特徴量の一覧も7個広げる。ID・目的変数・評価用の列・基準はそのまま。
    """

    def build(self, base: TrainingData, runs: pd.DataFrame) -> TrainingData:
        entries = pd.DataFrame({"race_id": base.ids[RACE_ID].to_numpy(), "horse_id": base.ids[HORSE_ID].to_numpy()},
                               index=base.features.index)
        rated = RatingTableBuilder().build(entries, runs)
        features = pd.concat([base.features, rated], axis=1)
        catalog = FeatureCatalog(base.catalog.features + HEAD_TO_HEAD_FEATURES)
        return TrainingData(base.ids, features, base.targets, base.evaluation, catalog, base.label_name,
                            base.class_labels, base.baseline)
