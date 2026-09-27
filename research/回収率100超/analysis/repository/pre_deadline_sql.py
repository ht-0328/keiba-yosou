"""締め切り前の断面（買う時点に見えるオッズ）を、レースごとに1つ選ぶ SQL の断片。"""

from __future__ import annotations

from .race_key_sql import JRA_ONLY, RACE_KEYS, RID

#: 使う断面のデータ区分（1 中間・2 前日売最終）。3 最終は締め切りの時点なので、買う時点には見えない。
PRE_DEADLINE_STAGES = "('1', '2')"


def pre_deadline_snapshot(parent_table: str) -> str:
    """``with`` の中身。``発走`` と ``断面`` の2つを作る。

    - ``発走``: 期間の中央のレースの rid と、断面を選ぶ締めの時刻（発走時刻の ``? `` 分前。``MMDDhhmm``）。
    - ``断面``: レースごとに、締めの時刻までに発表された締め切り前の断面のうち、いちばん新しいもの（rid・発表月日時分）。

    パラメータは順に、何分前か・最初の開催日（YYYYMMDD）・最後の開催日（YYYYMMDD）。
    """
    return f"""
    発走 as (
        select {RID} as rid,
            strftime(make_timestamp(cast(開催年 as bigint), cast(substr(開催月日, 1, 2) as bigint),
                                    cast(substr(開催月日, 3, 2) as bigint), cast(substr(発走時刻, 1, 2) as bigint),
                                    cast(substr(発走時刻, 3, 2) as bigint), 0.0)
                     - to_minutes(cast(? as bigint)), '%m%d%H%M') as cutoff
        from ra
        where 開催年 || 開催月日 between ? and ? and {JRA_ONLY} and データ区分 not in ('0', '9')
            and 発走時刻 not in ('', '0000')
        qualify row_number() over (partition by {RACE_KEYS} order by データ区分 desc, データ作成年月日 desc) = 1
    ),
    断面 as (
        select 発走.rid, h.発表月日時分 as announced
        from {parent_table} as h join 発走 on 発走.rid = {rid_of('h')}
        where h.データ区分 in {PRE_DEADLINE_STAGES} and h.発表月日時分 <= 発走.cutoff
        qualify row_number() over (partition by 発走.rid order by h.発表月日時分 desc) = 1
    )"""


def rid_of(alias: str) -> str:
    """別名つきの表から rid を作る式（``h.開催年 || h.開催月日 || …``）。"""
    return " || ".join(f"{alias}.{column.strip()}" for column in RACE_KEYS.split(","))
