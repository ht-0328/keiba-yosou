"""発走の何分前かまでに発表された、いちばん新しい締め切り前の断面のオッズ（時系列オッズ）を、券種ごとにレースごとに読む。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

#: レースの鍵6列をつないだ16桁（rid）。別名を {a} に入れて使う。
_RID = '{a}.開催年 || {a}.開催月日 || {a}.競馬場コード || {a}."開催回[第N回]" || {a}."開催日目[N日目]" || {a}.レース番号'
_RACE_KEYS = '開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号'


@dataclass(frozen=True)
class Board:
    """読む板: 親の表・子の表・組番の列・オッズの列。"""

    parent: str
    child: str
    combo: str
    odds: str


#: 時系列オッズがある板（JV-Data の時系列オッズは単複枠と馬連だけ）。
BOARDS: dict[str, Board] = {
    "単勝": Board("o1", '"o1__単勝オッズ"', "馬番", "オッズ"),
    "複勝最低": Board("o1", '"o1__複勝オッズ"', "馬番", "最低オッズ"),
    "複勝最高": Board("o1", '"o1__複勝オッズ"', "馬番", "最高オッズ"),
    "馬連": Board("o2", '"o2__馬連オッズ"', "組番", "オッズ"),
}


def _sql(board: Board) -> str:
    return f"""
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
        from {board.parent} as h join 発走 on 発走.race_id = {_RID.format(a='h')}
        where h.データ区分 in ('1', '2') and h.発表月日時分 <= 発走.cutoff
        qualify row_number() over (partition by 発走.race_id order by h.発表月日時分 desc) = 1
    )
    select 断面.race_id, trim(o.{board.combo}) as combo, try_cast(o.{board.odds} as double) / 10.0 as odds
    from 断面 join {board.child} as o on {_RID.format(a='o')} = 断面.race_id and o.発表月日時分 = 断面.announced
    where try_cast(o.{board.odds} as double) > 0
    order by 断面.race_id, combo
    """


class PreDeadlineBoardRepository:
    """期間の中央のレースについて、発走の ``minutes`` 分前までに発表された、いちばん新しい締め切り前の断面の板（``BOARDS`` の名前）を読む。
    列は ``race_id``・``combo``（馬番か組番。2桁ずつ）・``odds``（倍）。時系列オッズは JV-Data の提供が約1年ぶんなので、古いレースは行が無い。"""

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_day: date, last_day: date, minutes: int) -> None:
        self._connection = connection
        self._params = [minutes, first_day.strftime("%Y%m%d"), last_day.strftime("%Y%m%d")]

    def read(self, name: str) -> pd.DataFrame:
        return self._connection.execute(_sql(BOARDS[name]), self._params).fetch_df()
