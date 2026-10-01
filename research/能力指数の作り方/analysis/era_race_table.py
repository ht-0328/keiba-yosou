"""降級制度の廃止（2019年6月）の前と後で、レースの水準を別のものとして扱うレースの表。"""

from __future__ import annotations

import pandas as pd

from 共通.ability import FIELD_LEVEL, REFERENCE_LEVEL, RaceTable

#: 降級制度が廃止された最初の日（2019年の夏の開催から）。
REFORM_DAY = pd.Timestamp("2019-06-01")
#: 廃止の後の水準に付ける印。
_AFTER = "・廃止後"


class EraRaceTable(RaceTable):
    """``RaceTable`` と同じ表の、レースの水準に、2019年6月からのレースだけ「・廃止後」を付ける。

    例: 2020年の「2勝クラス・古馬」は「2勝クラス・古馬・廃止後」になり、基準タイムを求めるとき、2019年5月までの
    2勝クラス・古馬とは別の水準の差を持つ。基準の水準（1勝クラス・古馬）は、前後をつなぐため分けない。
    制度が変わってクラスの強さが変わったのに、水準の差を1つにしていることが、年ごとの当たり具合を下げていないかを確かめるのに使う。
    """

    def build(self, runs: pd.DataFrame) -> pd.DataFrame:
        races = super().build(runs)
        after = (pd.to_datetime(races["race_date"]) >= REFORM_DAY) & (races[FIELD_LEVEL] != REFERENCE_LEVEL)
        return races.assign(**{FIELD_LEVEL: races[FIELD_LEVEL].where(~after, races[FIELD_LEVEL] + _AFTER)})
