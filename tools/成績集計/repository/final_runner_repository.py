"""中央競馬の確定成績の出走（1行 = 1頭）を、``se`` と ``ra`` から直接読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

# 数える行の決め方（JV-Data 仕様書から決めた。事実表の SQL は写していない）:
# - データ区分 5・6（速報成績。全馬の着順が確定）と 7（月曜の成績）だけ。出走馬名表・出馬表（1・2）、中止（9）、地方・海外（A・B）は数えない。
# - 競馬場コード 01（札幌）〜 10（小倉）だけ。
_SQL = """
SELECT s."開催年" || s."開催月日" || s."競馬場コード" || s."開催回[第N回]" || s."開催日目[N日目]" || s."レース番号" AS rid,
       r."開催年" || r."開催月日" AS race_day,
       r."競馬場コード" AS venue_code,
       r."トラックコード" AS track_code,
       TRY_CAST(r."距離" AS INTEGER) AS distance,
       r."芝馬場状態コード" AS turf_going,
       r."ダート馬場状態コード" AS dirt_going,
       TRY_CAST(s."馬番" AS INTEGER) AS horse_no,
       TRY_CAST(s."枠番" AS INTEGER) AS frame_no,
       s."異常区分コード" AS abnormal,
       TRY_CAST(s."確定着順" AS INTEGER) AS finish,
       TRY_CAST(s."単勝人気順" AS INTEGER) AS popularity,
       TRY_CAST(s."単勝オッズ" AS INTEGER) AS odds_tenths,
       s."性別コード" AS sex_code,
       TRY_CAST(s."馬齢" AS INTEGER) AS age,
       trim(s."騎手名略称") AS jockey,
       trim(s."調教師名略称") AS trainer
FROM se AS s
JOIN ra AS r USING ("開催年", "開催月日", "競馬場コード", "開催回[第N回]", "開催日目[N日目]", "レース番号")
WHERE r."データ区分" IN ('5', '6', '7') AND s."データ区分" IN ('5', '6', '7')
  AND r."競馬場コード" BETWEEN '01' AND '10'
  AND r."開催年" || r."開催月日" BETWEEN ? AND ?
ORDER BY rid, horse_no
"""
#: 期間を指定しないときの両端（``YYYYMMDD`` の文字列で比べる）。
_FIRST_DAY, _LAST_DAY = "00000000", "99999999"


class FinalRunnerRepository:
    """確定成績の出走を読む。取消・除外の馬も含めて読み、出走に数えるかは読む側で決める。"""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, date_from: str | None, date_to: str | None) -> pd.DataFrame:
        """開催日が ``date_from``〜``date_to``（``YYYY-MM-DD``、両端を含む。None は端なし）の出走。"""
        first = date_from.replace("-", "") if date_from else _FIRST_DAY
        last = date_to.replace("-", "") if date_to else _LAST_DAY
        return self._con.execute(_SQL, [first, last]).fetchdf()
