"""距離の変更の傾向（まとまり R）を、対象の出走と過去の出走の2つのリポジトリから読んで数える。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from ..feature.history import DISTANCE_CHANGE_NAMES, DistanceChangeTendency
from ..repository import DistanceChangeRunRepository, DistanceChangeTargetRepository, TargetScope

#: 出走の行と突き合わせる鍵。
DISTANCE_CHANGE_KEY = ["race_id", "horse_id"]


class DistanceChangeRecordsLoader:
    """対象の出走（``DistanceChangeTargetRepository``）と、``first_day`` からの過去の平地の全出走（``DistanceChangeRunRepository``）を
    読み、出走ごと（race_id・horse_id）の距離の変更の傾向の 7列の表にする（``DistanceChangeTendency``）。SQL は持たない。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, first_day: date) -> None:
        self._targets = DistanceChangeTargetRepository(con)
        self._runs = DistanceChangeRunRepository(con, first_day)

    def read(self, scope: TargetScope) -> pd.DataFrame:
        """列は ``DISTANCE_CHANGE_KEY`` と ``DISTANCE_CHANGE_NAMES``。"""
        targets = self._targets.read(scope)
        tendency = DistanceChangeTendency().of(targets, self._runs.read(scope))
        return pd.concat([targets[DISTANCE_CHANGE_KEY], tendency[list(DISTANCE_CHANGE_NAMES)]], axis=1)
