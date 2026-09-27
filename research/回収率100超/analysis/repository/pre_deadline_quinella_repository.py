"""締め切り前の馬連オッズから、馬ごとの2着以内の確率を、レースごとに1つの断面で読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from .pre_deadline_sql import pre_deadline_snapshot, rid_of

#: 作る列。確定オッズから作る ``PoolMarginal("quinella_top2")`` と同じ名前・同じ作り。
COLUMN = "馬連から見た2着以内率"

_SQL = f"""
with {pre_deadline_snapshot("o2")},
オッズ as (
    select 断面.rid, o.組番 as combo, 1.0 / (try_cast(o.オッズ as double) / 10.0) as inverse
    from 断面 join o2__馬連オッズ as o on {rid_of("o")} = 断面.rid and o.発表月日時分 = 断面.announced
    where try_cast(o.オッズ as double) > 0
),
合計 as (select rid, sum(inverse) as total from オッズ group by rid),
ばらす as (
    select rid, try_cast(substr(combo, (位置.i - 1) * 2 + 1, 2) as integer) as horse_no, inverse
    from オッズ cross join (select unnest(range(1, 3)) as i) as 位置
)
select ばらす.rid, ばらす.horse_no, sum(ばらす.inverse) / max(合計.total) as "{COLUMN}"
from ばらす join 合計 on 合計.rid = ばらす.rid
group by ばらす.rid, ばらす.horse_no
"""


class PreDeadlineQuinellaRepository:
    """期間の中央のレースについて、発走の ``minutes`` 分前までに発表された、いちばん新しい馬連の断面から、
    馬ごとの「組に入る確率」（市場が見た2着以内の確率）を読む。作り方は確定オッズのときと同じ。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_day: date, last_day: date, minutes: int) -> None:
        self._connection = connection
        self._params = [minutes, first_day.strftime("%Y%m%d"), last_day.strftime("%Y%m%d")]

    def read(self) -> pd.DataFrame:
        """``rid``・``horse_no``・``馬連から見た2着以内率``。"""
        return self._connection.execute(_SQL, self._params).fetch_df()
