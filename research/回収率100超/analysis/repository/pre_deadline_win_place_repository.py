"""締め切り前の単勝・複勝オッズを、レースごとに1つの断面で読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from .pre_deadline_sql import pre_deadline_snapshot, rid_of

_SQL = f"""
with {pre_deadline_snapshot("o1")}
select 断面.rid, 断面.announced, try_cast(t.馬番 as integer) as horse_no,
    nullif(try_cast(t.オッズ as double), 0) / 10.0 as win_odds,
    nullif(try_cast(p.最低オッズ as double), 0) / 10.0 as place_odds_low,
    nullif(try_cast(p.最高オッズ as double), 0) / 10.0 as place_odds_high
from 断面
join o1__単勝オッズ as t on {rid_of("t")} = 断面.rid and t.発表月日時分 = 断面.announced
left join o1__複勝オッズ as p
    on {rid_of("p")} = 断面.rid and p.発表月日時分 = 断面.announced and p.馬番 = t.馬番
where try_cast(t.馬番 as integer) is not null
"""


class PreDeadlineWinPlaceRepository:
    """期間の中央のレースについて、発走の ``minutes`` 分前までに発表された、いちばん新しい単複枠の断面を読む。

    断面は時系列オッズ（``0B41``）か速報オッズ（``0B30``）で元DB に入ったもの。無いレースは行が出ない。
    取消でオッズが付かない馬は、オッズが欠けた行になる。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_day: date, last_day: date, minutes: int) -> None:
        self._connection = connection
        self._params = [minutes, first_day.strftime("%Y%m%d"), last_day.strftime("%Y%m%d")]

    def read(self) -> pd.DataFrame:
        """``rid``・``announced``・``horse_no``・``win_odds``・``place_odds_low``・``place_odds_high``。"""
        return self._connection.execute(_SQL, self._params).fetch_df()
