"""元DB（中央か地方。se と ra は同じ列）から、1つの競馬場の期間内の出走（1行 = 1頭）を読む。馬場の傾向を数えるため。"""

from __future__ import annotations

from datetime import date

import duckdb
import pandas as pd

from 共通.codes import surface_sql

#: レースの鍵（se と ra で同じ）。
_KEYS = '開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号'
#: 競馬場と期間（開催年||開催月日 の 'YYYYMMDD'）で絞った出走。同じ馬の行が複数あれば、データ区分・作成日の新しい行。
#: 位置は 4コーナーの順位（無ければ 3・2・1コーナーの順に、最後に回ったコーナー）。
_SQL = f"""
WITH s AS (
    SELECT {_KEYS}, 馬番, 確定着順,
           "1コーナーでの順位" AS c1, "2コーナーでの順位" AS c2, "3コーナーでの順位" AS c3, "4コーナーでの順位" AS c4
    FROM se
    WHERE 競馬場コード = ? AND 開催年 || 開催月日 BETWEEN ? AND ?
    QUALIFY row_number() OVER (PARTITION BY {_KEYS}, 馬番 ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
), r AS (
    SELECT {_KEYS}, トラックコード
    FROM ra
    WHERE 競馬場コード = ? AND 開催年 || 開催月日 BETWEEN ? AND ?
    QUALIFY row_number() OVER (PARTITION BY {_KEYS} ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
)
SELECT s.開催年 || s.開催月日 AS race_day,
       s.開催年 || s.開催月日 || s.競馬場コード || s."開催回[第N回]" || s."開催日目[N日目]" || s.レース番号 AS race_id,
       TRY_CAST(s.レース番号 AS INTEGER) AS race_no,
       {surface_sql("r.トラックコード")} AS surface,
       r.トラックコード = '10' AS straight,
       TRY_CAST(NULLIF(s.確定着順, '00') AS INTEGER) AS finish,
       coalesce(TRY_CAST(NULLIF(s.c4, '00') AS INTEGER), TRY_CAST(NULLIF(s.c3, '00') AS INTEGER),
                TRY_CAST(NULLIF(s.c2, '00') AS INTEGER), TRY_CAST(NULLIF(s.c1, '00') AS INTEGER)) AS corner
FROM s JOIN r USING (開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号)
ORDER BY race_day, race_no, s.馬番
"""


class VenueRunRepository:
    """列は ``race_day``（'YYYYMMDD'）・``race_id``（16桁）・``race_no``・``surface``（芝・ダート・障害。わからなければ ?）・
    ``straight``（芝・直線のコース。コーナーが無い）・``finish``（確定着順。まだ無い・付かないなら欠損値）・``corner``（最後に回ったコーナーの順位。直線のコースなどは欠損値）。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, venue_code: str, first_day: date, last_day: date) -> pd.DataFrame:
        span = (venue_code, f"{first_day:%Y%m%d}", f"{last_day:%Y%m%d}")
        return self._con.execute(_SQL, [*span, *span]).df()
