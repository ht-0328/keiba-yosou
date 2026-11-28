"""発走の何分前かまでに発表された、いちばん新しい締め切り前の単勝オッズ（時系列オッズ ``o1`` の断面）を、レースごとに読む。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

#: レースの鍵6列をつないだ16桁（rid）。別名を {a} に入れて使う。
_RID = '{a}.開催年 || {a}.開催月日 || {a}.競馬場コード || {a}."開催回[第N回]" || {a}."開催日目[N日目]" || {a}.レース番号'
_RACE_KEYS = '開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号'
#: 締め切り前の断面のデータ区分（1 中間・2 前日売最終）。
_PRE_DEADLINE_STAGES = "('1', '2')"

_SQL = f"""
with 発走 as (
    select {_RID.format(a='ra')} as race_id,
        strftime(make_timestamp(cast(開催年 as bigint), cast(substr(開催月日, 1, 2) as bigint), cast(substr(開催月日, 3, 2) as bigint),
                 cast(substr(発走時刻, 1, 2) as bigint), cast(substr(発走時刻, 3, 2) as bigint), 0.0) - to_minutes(cast(? as bigint)),
                 '%m%d%H%M') as cutoff
    from ra
    where 開催年 || 開催月日 between ? and ? and 競馬場コード between '01' and '10'
      and データ区分 not in ('0', '9') and 発走時刻 not in ('', '0000')
    qualify row_number() over (partition by {_RACE_KEYS} order by データ区分 desc, データ作成年月日 desc) = 1
), 断面 as (
    select 発走.race_id, h.発表月日時分 as announced
    from o1 as h join 発走 on 発走.race_id = {_RID.format(a='h')}
    where h.データ区分 in {_PRE_DEADLINE_STAGES} and h.発表月日時分 <= 発走.cutoff
    qualify row_number() over (partition by 発走.race_id order by h.発表月日時分 desc) = 1
)
select 断面.race_id, try_cast(o.馬番 as integer) as horse_no, try_cast(o.オッズ as double) / 10.0 as odds
from 断面 join "o1__単勝オッズ" as o on {_RID.format(a='o')} = 断面.race_id and o.発表月日時分 = 断面.announced
where try_cast(o.オッズ as double) > 0
order by 断面.race_id, horse_no
"""


class PreDeadlineWinOddsRepository:
    """期間の中央のレースについて、発走の ``minutes`` 分前までに発表された、いちばん新しい締め切り前の単勝オッズを馬ごとに読む。

    時系列オッズは JV-Data の提供が約1年ぶんなので、古いレースは行が無い。列は ``race_id``・``horse_no``・``odds``（倍）。
    発表の時刻は月日時分しか無いので、年をまたぐ前日の断面は選べない（当日の断面だけで足りる）。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_day: date, last_day: date, minutes: int) -> None:
        self._connection = connection
        self._params = [minutes, first_day.strftime("%Y%m%d"), last_day.strftime("%Y%m%d")]

    def read(self) -> pd.DataFrame:
        return self._connection.execute(_SQL, self._params).fetch_df()
