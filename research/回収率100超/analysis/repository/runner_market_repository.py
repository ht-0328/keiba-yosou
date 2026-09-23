"""1行 = 1頭の出走に、確定オッズ・結果・払戻を並べた表を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from .race_key_sql import FINAL_STAGES, JRA_ONLY, RACE_KEYS, RID

#: 読み出す SQL。1頭ぶんの「市場が付けた値（単勝・複勝のオッズ）」と「結果」をそろえる。
_SQL = f"""
with 出走 as (
    select {RID} as rid,
        try_cast(馬番 as integer) as horse_no,
        血統登録番号 as horse_id,
        try_cast(確定着順 as integer) as finish,
        異常区分コード as abnormal,
        try_cast(単勝人気順 as integer) as popularity,
        try_cast(単勝オッズ as double) / 10.0 as se_win_odds,
        row_number() over (partition by {RACE_KEYS}, 馬番
            order by データ区分 desc, データ作成年月日 desc) as rn
    from se
    where データ区分 in {FINAL_STAGES} and {JRA_ONLY} and 開催年 >= '{{first_year}}'
),
レース as (
    select {RID} as rid,
        cast(開催年 || '-' || substr(開催月日, 1, 2) || '-' || substr(開催月日, 3, 2) as date) as race_date,
        競馬場コード as venue_code,
        try_cast(レース番号 as integer) as race_no,
        トラックコード as track_code,
        try_cast(距離 as integer) as distance_m,
        グレードコード as grade_code,
        競走種別コード as kind_code,
        case when トラックコード between '23' and '29'
             then "ダート馬場状態コード" else "芝馬場状態コード" end as condition_code,
        row_number() over (partition by {RACE_KEYS}
            order by データ区分 desc, データ作成年月日 desc) as rn
    from ra
    where データ区分 in {FINAL_STAGES} and {JRA_ONLY} and 開催年 >= '{{first_year}}'
),
単勝オッズ as (
    select rid, horse_no, win_odds from (
        select {RID} as rid, try_cast(馬番 as integer) as horse_no,
            try_cast(オッズ as double) / 10.0 as win_odds,
            row_number() over (partition by {RACE_KEYS}, 馬番 order by 発表月日時分 desc) as rn
        from o1__単勝オッズ where 開催年 >= '{{first_year}}' and {JRA_ONLY}
    ) where rn = 1
),
複勝オッズ as (
    select rid, horse_no, place_odds_low, place_odds_high from (
        select {RID} as rid, try_cast(馬番 as integer) as horse_no,
            try_cast(最低オッズ as double) / 10.0 as place_odds_low,
            try_cast(最高オッズ as double) / 10.0 as place_odds_high,
            row_number() over (partition by {RACE_KEYS}, 馬番 order by 発表月日時分 desc) as rn
        from o1__複勝オッズ where 開催年 >= '{{first_year}}' and {JRA_ONLY}
    ) where rn = 1
),
単勝払戻 as (
    select {RID} as rid, try_cast(馬番 as integer) as horse_no,
        max(try_cast(払戻金 as integer)) as win_payout
    from hr__単勝払戻 where 開催年 >= '{{first_year}}' and try_cast(馬番 as integer) is not null
    group by all
),
複勝払戻 as (
    select {RID} as rid, try_cast(馬番 as integer) as horse_no,
        max(try_cast(払戻金 as integer)) as place_payout
    from hr__複勝払戻 where 開催年 >= '{{first_year}}' and try_cast(馬番 as integer) is not null
    group by all
)
select 出走.rid, レース.race_date, レース.venue_code, レース.race_no, レース.track_code,
    レース.distance_m, レース.grade_code, レース.kind_code, レース.condition_code,
    出走.horse_no, 出走.horse_id, 出走.finish, 出走.abnormal, 出走.popularity,
    coalesce(単勝オッズ.win_odds, 出走.se_win_odds) as win_odds,
    複勝オッズ.place_odds_low, 複勝オッズ.place_odds_high,
    coalesce(単勝払戻.win_payout, 0) as win_payout,
    coalesce(複勝払戻.place_payout, 0) as place_payout
from 出走
join レース on レース.rid = 出走.rid and レース.rn = 1
left join 単勝オッズ on 単勝オッズ.rid = 出走.rid and 単勝オッズ.horse_no = 出走.horse_no
left join 複勝オッズ on 複勝オッズ.rid = 出走.rid and 複勝オッズ.horse_no = 出走.horse_no
left join 単勝払戻 on 単勝払戻.rid = 出走.rid and 単勝払戻.horse_no = 出走.horse_no
left join 複勝払戻 on 複勝払戻.rid = 出走.rid and 複勝払戻.horse_no = 出走.horse_no
where 出走.rn = 1
"""


class RunnerMarketRepository:
    """出走 × 市場（確定オッズ）× 結果 × 払戻 の表を読む。

    単勝オッズは ``o1`` のものを使い、無ければ ``se`` の値で埋める。複勝オッズは発表の幅（最低・最高）を
    そのまま持つ。JRA は複勝の払戻を「どの馬が一緒に来たか」で変えるので、1つの値には決まらない。
    精算には ``hr`` の確定払戻を使う。
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection, first_year: int = 2016) -> None:
        self._connection = connection
        self._first_year = first_year

    def read(self) -> pd.DataFrame:
        """1行 = 1頭の出走の表。"""
        return self._connection.execute(_SQL.format(first_year=self._first_year)).fetch_df()
