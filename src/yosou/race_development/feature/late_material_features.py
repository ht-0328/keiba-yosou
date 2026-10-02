"""U. 後半の材料（1レースごと 7個）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import RaceRecords, as_numbers

from .history import COUNT, MEAN, SECOND_HALF_BASELINE, STD, RaceBaselineLookup

#: 「末脚のある馬」とみなす、近5走の上がりの速さの平均の線（設計書 09 の U）。
CLOSER_LINE = 0.3


class LateMaterialFeatures:
    """U. 後半タイムの基準と、末脚のある馬の集まり具合（設計書 09 の U）。``RaceFeatureGroup`` を守る。⑥だけで使う。"""

    def __init__(self) -> None:
        self._baselines = RaceBaselineLookup()

    def build(self, records: RaceRecords) -> pd.DataFrame:
        races, features, race = records.races, records.horse_features, records.entries["race_id"]
        baselines = self._baselines.of(records.race_results, races)
        closing = as_numbers(features["近5走の上がりの速さの平均"])
        against_race = as_numbers(features["近5走の上がりとレースの後半タイムとの差の平均"])
        aggregated = pd.DataFrame({
            "近5走の上がりの速さの平均の最小": closing.groupby(race, sort=False).min(),
            "近5走の上がりの速さの平均が 0.3 以下の馬の数":
                (closing <= CLOSER_LINE).astype("float64").groupby(race, sort=False).sum(),
            "近5走の上がりとレースの後半タイムとの差の平均の、レースの平均": against_race.groupby(race, sort=False).mean(),
            "上がりの記録が無い馬の割合": closing.isna().astype("float64").groupby(race, sort=False).mean(),
        })
        return pd.concat([pd.DataFrame({
            SECOND_HALF_BASELINE: baselines[SECOND_HALF_BASELINE + MEAN],
            "後半タイムの基準の標準偏差": baselines[SECOND_HALF_BASELINE + STD],
            "後半タイムの基準の件数": baselines[SECOND_HALF_BASELINE + COUNT],
        }, index=races.index), aggregated.reindex(races.index)], axis=1)
