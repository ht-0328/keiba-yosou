"""Q. 前半タイムの基準とコース（6個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import RaceRecords

from .history import (
    COUNT,
    FIRST_CORNER,
    FIRST_HALF_BASELINE,
    LEADER_POSITION,
    MEAN,
    MEASURED_METERS,
    STD,
    RaceBaselineLookup,
)


class PaceBaselineFeatures:
    """Q. 前半タイムの基準と、コースの形の2個（設計書 09 の Q）。``RaceFeatureGroup`` を守る。

    基準は、レースごとの結果（``PaceRecordSource`` が基準を付けた表）から引く。予測するレースは、まだ結果の表に無いので、
    同じ ``PaceBaseline`` で付け直す（``RaceBaselineLookup``）。基準の列（平均・標準偏差・件数）だけを読み、
    そのレース自身の前半タイムは読まない（設計書 11 の 8）。
    """

    def __init__(self) -> None:
        self._baselines = RaceBaselineLookup()

    def build(self, records: RaceRecords) -> pd.DataFrame:
        races = records.races
        baselines = self._baselines.of(records.race_results, races)
        course = records.horse_features[[FIRST_CORNER, LEADER_POSITION]].groupby(records.entries["race_id"], sort=False).first()
        return pd.DataFrame({
            MEASURED_METERS: baselines[MEASURED_METERS],
            FIRST_HALF_BASELINE: baselines[FIRST_HALF_BASELINE + MEAN],
            "基準の標準偏差": baselines[FIRST_HALF_BASELINE + STD],
            "基準の件数": baselines[FIRST_HALF_BASELINE + COUNT],
            FIRST_CORNER: course[FIRST_CORNER],
            LEADER_POSITION: course[LEADER_POSITION],
        }, index=races.index)
