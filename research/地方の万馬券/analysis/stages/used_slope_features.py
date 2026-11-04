"""当日の馬場傾向のレースの値（使う内の傾き・使う前の傾き）を、レース単位の特徴量にする。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import Feature, FeatureKind, PredictionTiming, RaceRecords
from yosou.track_bias import names

#: 特徴量の名前（U。当日から分かる）。
USED_INNER, USED_FRONT = "当日の使う内の傾き", "当日の使う前の傾き"
NAMES: tuple[str, ...] = (USED_INNER, USED_FRONT)
FEATURES: tuple[Feature, ...] = tuple(Feature(name, "U", FeatureKind.NUMERIC, PredictionTiming.RACE_DAY) for name in NAMES)


def race_slopes_table(history: pd.DataFrame) -> pd.DataFrame:
    """``LocalBiasHistory.of`` の表（1行 = 1頭）から、レースごとの使う傾き（index は race_id、列は ``NAMES``）。"""
    by_race = history.groupby(names.RACE_ID, sort=False)[[names.INNER_SLOPE_FEATURE, names.FRONT_SLOPE_FEATURE]].first()
    return by_race.rename(columns={names.INNER_SLOPE_FEATURE: USED_INNER, names.FRONT_SLOPE_FEATURE: USED_FRONT}).astype("float64")


class UsedSlopeFeatures:
    """``RaceFeatureGroup`` を守る。レースごとの使う傾きの表（``race_slopes_table``）を受け取り、対象のレースの行を返す。
    表に無いレース（傾きの元が無い）は欠損値。"""

    def __init__(self, table: pd.DataFrame) -> None:
        self._table = table.reindex(columns=list(NAMES))
        self._table.index = self._table.index.astype(str)

    def build(self, records: RaceRecords) -> pd.DataFrame:
        return self._table.reindex(pd.Index(records.race_ids).astype(str)).set_axis(records.race_ids)
