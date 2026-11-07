"""元DB（中央か地方。se と ra は同じ列）から、1レースの出走馬それぞれの、そのレースより前の走の脚質の材料を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

#: 中央の競馬場コードの範囲（札幌 01 〜 小倉 10）。地方は ``共通.local_codes.LOCAL_VENUE_RANGE``。
JRA_VENUES: tuple[str, str] = ("01", "10")
#: レースの鍵（se と ra で同じ）。
_KEYS = '開催年, 開催月日, 競馬場コード, "開催回[第N回]", "開催日目[N日目]", レース番号'
#: そのレースの出走馬（馬番と血統登録番号）と、その馬たちの、レースの日より前の走（脚質の判定・最初のコーナーの順位・頭数）。
#: 走は競馬場コードの範囲（中央の DB なら中央の競馬場、地方の DB なら地方の競馬場。事実表と同じ）に絞る。
#: 最初のコーナーは、事実表と同じくコーナー通過順位の表（ra__コーナー通過順位）で最初に記録されたコーナー。2周目以降が記録に混ざる
#: レースと、通過順位の記録が無いレースは4コーナーの順位。同じ行が複数あれば、データ区分・作成日の新しい行。
#: 判定もコーナーの順位も無い走（出走していない・直線のコース）は読まない。
_SQL = f"""
WITH entry AS (
    SELECT 馬番, 血統登録番号
    FROM se
    WHERE 開催年 = ? AND 開催月日 = ? AND 競馬場コード = ? AND "開催回[第N回]" = ? AND "開催日目[N日目]" = ? AND レース番号 = ?
    QUALIFY row_number() OVER (PARTITION BY 馬番 ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
), past AS (
    SELECT {_KEYS}, 血統登録番号, 開催年 || 開催月日 AS race_day, 今回レース脚質判定 AS style_code,
           TRY_CAST(NULLIF("1コーナーでの順位", '00') AS INTEGER) AS c1, TRY_CAST(NULLIF("2コーナーでの順位", '00') AS INTEGER) AS c2,
           TRY_CAST(NULLIF("3コーナーでの順位", '00') AS INTEGER) AS c3, TRY_CAST(NULLIF("4コーナーでの順位", '00') AS INTEGER) AS c4
    FROM se
    WHERE 血統登録番号 IN (SELECT 血統登録番号 FROM entry) AND 開催年 || 開催月日 < ? AND 競馬場コード BETWEEN ? AND ?
    QUALIFY row_number() OVER (PARTITION BY {_KEYS}, 血統登録番号 ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
), races AS (
    SELECT DISTINCT {_KEYS} FROM past
), field AS (
    SELECT {_KEYS}, TRY_CAST(出走頭数 AS INTEGER) AS field_size
    FROM ra JOIN races USING ({_KEYS})
    QUALIFY row_number() OVER (PARTITION BY {_KEYS} ORDER BY データ区分 DESC, データ作成年月日 DESC) = 1
), corners AS (
    SELECT {_KEYS}, arg_min(TRY_CAST(コーナー AS INTEGER), TRY_CAST("_連番" AS INTEGER)) AS first_corner_no,
           coalesce(max(TRY_CAST(周回数 AS INTEGER)), 1) > 1 AS laps_over_one
    FROM ra__コーナー通過順位 JOIN races USING ({_KEYS})
    WHERE trim(各通過順位) <> ''
    GROUP BY {_KEYS}
), ranked AS (
    SELECT past.*, field.field_size,
           coalesce(CASE WHEN coalesce(corners.laps_over_one, FALSE) THEN NULL
                         WHEN corners.first_corner_no = 1 THEN past.c1 WHEN corners.first_corner_no = 2 THEN past.c2
                         WHEN corners.first_corner_no = 3 THEN past.c3 WHEN corners.first_corner_no = 4 THEN past.c4 END,
                    past.c4) AS corner
    FROM past LEFT JOIN field USING ({_KEYS}) LEFT JOIN corners USING ({_KEYS})
)
SELECT TRY_CAST(entry.馬番 AS INTEGER) AS horse_no, ranked.race_day, ranked.style_code, ranked.corner, ranked.field_size
FROM entry
JOIN ranked USING (血統登録番号)
WHERE ranked.style_code IN ('1', '2', '3', '4') OR ranked.corner IS NOT NULL
ORDER BY horse_no, ranked.race_day DESC, ranked.レース番号 DESC
"""


class PastStyleRepository:
    """列は ``horse_no``・``race_day``（'YYYYMMDD'）・``style_code``（レース後の脚質の判定 1 逃げ〜4 追込。地方は空）・
    ``corner``（最初のコーナーの順位）・``field_size``（出走頭数）。馬番ごとに新しい走から並ぶ。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, venues: tuple[str, str] = JRA_VENUES) -> None:
        self._con = con
        self._venues = venues

    def read(self, rid: str) -> pd.DataFrame:
        keys = (rid[:4], rid[4:8], rid[8:10], rid[10:12], rid[12:14], rid[14:16])
        return self._con.execute(_SQL, [*keys, rid[:8], *self._venues]).df()
