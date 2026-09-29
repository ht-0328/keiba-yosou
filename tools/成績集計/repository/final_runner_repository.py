"""中央競馬の確定成績の出走（1行 = 1頭）を、``se`` と ``ra`` から直接読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

# 数える行の決め方（JV-Data 仕様書から決めた。事実表の SQL は写していない）:
# - データ区分 5・6（速報成績。全馬の着順が確定）と 7（月曜の成績）だけ。出走馬名表・出馬表（1・2）、中止（9）、地方・海外（A・B）は読まない。
# - 競馬場コード 01（札幌）〜 10（小倉）だけ。
# - 期間では絞らない。前走を探すのに、数える期間より前の出走も要るため（期間は読む側で絞る）。
_SQL = """
SELECT s."開催年" || s."開催月日" || s."競馬場コード" || s."開催回[第N回]" || s."開催日目[N日目]" || s."レース番号" AS rid,
       r."開催年" || r."開催月日" AS race_day,
       r."競馬場コード" AS venue_code,
       r."トラックコード" AS track_code,
       TRY_CAST(r."距離" AS INTEGER) AS distance,
       r."芝馬場状態コード" AS turf_going,
       r."ダート馬場状態コード" AS dirt_going,
       r."競走条件コード 最若年条件" AS condition_code,
       trim(r."グレードコード") AS grade_code,
       TRY_CAST(r."出走頭数" AS INTEGER) AS starters,
       TRY_CAST(r."登録頭数" AS INTEGER) AS entries,
       s."血統登録番号" AS horse_id,
       trim(s."馬名") AS horse_name,
       TRY_CAST(s."馬番" AS INTEGER) AS horse_no,
       TRY_CAST(s."枠番" AS INTEGER) AS frame_no,
       s."異常区分コード" AS abnormal,
       TRY_CAST(s."確定着順" AS INTEGER) AS finish,
       TRY_CAST(s."単勝人気順" AS INTEGER) AS popularity,
       TRY_CAST(s."単勝オッズ" AS INTEGER) AS odds_tenths,
       s."性別コード" AS sex_code,
       TRY_CAST(s."馬齢" AS INTEGER) AS age,
       trim(s."騎手名略称") AS jockey,
       trim(s."調教師名略称") AS trainer,
       TRY_CAST(s."馬体重" AS INTEGER) AS body_weight_raw,
       s."増減符号" AS weight_sign,
       TRY_CAST(s."増減差" AS INTEGER) AS weight_diff,
       TRY_CAST(s."後3ハロンタイム" AS INTEGER) AS last3f_tenths,
       s."今回レース脚質判定" AS style_code,
       TRY_CAST(s."マイニング予想順位" AS INTEGER) AS dm_rank_raw
FROM se AS s
JOIN ra AS r USING ("開催年", "開催月日", "競馬場コード", "開催回[第N回]", "開催日目[N日目]", "レース番号")
WHERE r."データ区分" IN ('5', '6', '7') AND s."データ区分" IN ('5', '6', '7')
  AND r."競馬場コード" BETWEEN '01' AND '10'
ORDER BY rid, horse_no
"""


class FinalRunnerRepository:
    """確定成績の出走を、DB の全期間ぶん読む。取消・除外の馬も含めて読み、出走に数えるかは読む側で決める。

    値は仕様書の桁のまま数にしただけ（``odds_tenths`` は 10 倍、``last3f_tenths`` も 10 倍、無しは 0 か 999）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self) -> pd.DataFrame:
        return self._con.execute(_SQL).fetchdf()
