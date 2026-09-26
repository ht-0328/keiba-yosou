"""A. レースの条件（11個）。"""

from __future__ import annotations

import pandas as pd

from .race_records import RaceRecords
from .value_types import as_yes_no

#: 1頭ごとの特徴量（手本の A）から、レースの1頭目の値をそのまま使うもの。
COPIED_FROM_HORSE: tuple[str, ...] = ("競馬場", "芝ダ", "コース", "距離", "馬場状態", "クラス", "開催月", "牡馬と牝馬が一緒に走るか")
#: レース単位で作る特徴量の名前。
GOING = "馬場状態"
FIELD_SIZE = "出走頭数"
SPECIAL_RACE = "特別戦か"
HANDICAP = "ハンデ戦か"
#: 事実表の重量種別の、ハンデ戦の値。
_HANDICAP_TYPE = "ハンデ"


class RaceConditionSummary:
    """A. レースの条件。同じレースの馬はみな同じ値なので、1頭目の値を使う。``RaceFeatureGroup`` を守る。

    出走頭数は、その時点で出走する馬の数（学習は出走した馬、予測は取消・除外になっていない馬。荒れ具合の設計書 11 の 10）。
    荒れ具合の予想の A と、展開の予想の R で使う（展開の設計書 04 の 2。予想のパッケージどうしは参照しないので ``shared`` に置く）。
    """

    def build(self, records: RaceRecords) -> pd.DataFrame:
        entries = records.entries
        race = entries["race_id"]
        copied = records.horse_features[list(COPIED_FROM_HORSE)].groupby(race, sort=False).first()
        race_rows = records.races
        return copied.assign(**{
            FIELD_SIZE: race.groupby(race, sort=False).size(),
            SPECIAL_RACE: as_yes_no(race_rows["race_name"].fillna("").astype("str").str.strip() != ""),
            HANDICAP: as_yes_no(race_rows["weight_type"] == _HANDICAP_TYPE),
        })
