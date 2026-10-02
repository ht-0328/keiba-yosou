"""元の学習データの表に、展開の予想の結果（まとまり P）の 20列を足す。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData
from yosou.shared.feature import FeatureCatalog
from yosou.shared.feature.pace_forecast import PaceForecastTableBuilder


class PaceTableBuilder:
    """``base`` の行（目的変数・評価用の列・基準もそのまま）に、同じ出走（レースID・馬ID）の P の 20列を足す。

    P は予想のパッケージと同じ部品（``PaceForecastTableBuilder``）で、展開の予想の元の予測の表（``forecasts``）から作る。
    予測の無い出走（展開の予測が始まる前の年など）は欠損値。特徴量の一覧は ``catalog``。
    """

    def build(self, base: TrainingData, forecasts: pd.DataFrame, catalog: FeatureCatalog) -> TrainingData:
        pace = PaceForecastTableBuilder().build(base.ids[RACE_ID], base.ids[HORSE_ID], forecasts)
        features = pd.concat([base.features, pace.set_axis(base.features.index)], axis=1)
        return replace(base, features=features[list(catalog.names)], catalog=catalog)
