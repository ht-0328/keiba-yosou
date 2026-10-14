"""出走ごとの「材料の締めの日」を決める。"""

from __future__ import annotations

import pandas as pd

#: 材料の締めの日の列（対象の関係にあるとき。``TargetScope.as_of_column``）。
AS_OF_DATE = "as_of_date"
_ONE_DAY = pd.Timedelta(days=1)


class MaterialCutoff:
    """日付で区切って数える材料（通算と直近の成績・対戦レーティング）を、どの日までの記録で数えるか。

    行に ``as_of_date``（材料の締めの日。特別登録の予想では登録日相当）があればその日（その日を含む）、
    無ければ（欠損値も）開催日の前日。中央の予想は列を持たないので、今までどおり前日までになる
    （特別登録の予想の設計書 11 の 6）。
    """

    def of(self, rows: pd.DataFrame) -> pd.Series:
        """行ごとの締めの日（日付型。その日を含む）。行の並びと index は ``rows`` と同じ。"""
        day_before = pd.to_datetime(rows["race_date"]) - _ONE_DAY
        if AS_OF_DATE not in rows.columns:
            return day_before
        as_of = pd.to_datetime(rows[AS_OF_DATE], errors="coerce")
        return as_of.where(as_of.notna(), day_before)

    def next_day_of(self, rows: pd.DataFrame) -> pd.Series:
        """締めの日の翌日（「その日より前を数える」部品に渡す日）。"""
        return self.of(rows) + _ONE_DAY
