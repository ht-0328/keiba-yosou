"""条件ごとの、前日までの1年の荒れ率。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .top3_rate import Top3Rate

#: 日ごとの表の列の名前（その日のレース数と、そのうち中荒れ以上だったレース数）。
RACES, UPSETS = "races", "upsets"
#: ``Top3Rate`` の日ごとの表の列の名前への読み替え。
_AS_TOP3_COLUMNS = {RACES: "starts", UPSETS: "places"}


class ConditionUpsetRate:
    """レースごとに、同じ条件（競馬場・芝ダ・距離帯、クラス など）のレースが、開催日の前日までの 365日で
    中荒れ以上だった割合を出す（荒れ具合の設計書 09 の E）。

    作りは ``Top3Rate`` と同じ（日ごとの数を累計にして、「前日までの累計 − 366日前までの累計」で数える）。
    ``races`` はレースごとの行（``race_date`` と、条件の鍵の列 ``key_column`` を持つ）。
    中荒れ以上かどうかは、呼ぶ側が券種ごとの線引きで決めて、日ごとの表にしてから渡す。
    """

    def __init__(self, races: pd.DataFrame, key_column: str) -> None:
        self._races = races
        self._rate = Top3Rate(races, key_column, key_column)

    def of(self, days: pd.DataFrame) -> pd.Series:
        """``days`` は鍵ごと・開催日ごとの ``races``（レース数）と ``upsets``（中荒れ以上の数）。
        期間にレースが無ければ欠損値。index は ``races`` と同じ。
        """
        if days.empty:
            return pd.Series(np.nan, index=self._races.index, dtype="float64")
        return self._rate.of(days.rename(columns=_AS_TOP3_COLUMNS))
